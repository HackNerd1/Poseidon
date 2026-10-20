#!/usr/bin/env python3
"""岗位预过滤：把搜索快照压成小而干净的候选集。薪资折算、岗位名门禁、去重在此完成，
模型只对剩余项打分，不再逐条读原始 JSON 心算薪资。

为什么放脚本侧（2026-10-20 实测）：160 条原始岗位整份进上下文是最大 token 消耗点；
且当时 parse_salary 对兼职四类单位全返回 null，硬过滤形同虚设，靠模型对话里临时脚本补。

用法:
    python filter.py                          # 自动取 BOSS_DIR 下最新 jobs-*.json
    python filter.py --jobs jobs-2026-10-20.json [--config-path config.json]

输出（BOSS_DIR 下，日期取 jobs 快照的 fetchedAt）:
    candidates-<日期>.json   # 候选 + 边界，模型只需要读这一个文件
    screen-<日期>.json       # 全量审计：每条的去向与原因、淘汰统计，调阈值时才读
stdout 末行: RESULT <candidates路径>
退出码: 0 成功 / 1 输入缺失或配置不足（CONFIG_MISSING 需补问用户，不得用默认值折算）
"""
import argparse
import re
import sys
import time
from pathlib import Path

from _lib import (BOSS_DIR, CITIES, CONFIG_PATH, DEFAULT_CONFIG, config_gaps,
                  parse_salary, read_json, write_json)

# 折算常量与依据：
HARD_CUT = 0.85             # matching.md：上限低于期望下限的 85% 才算硬伤，留 15% 谈判空间
WIDE_RATIO = 3.0            # 上限/下限 ≥ 3 的宽幅薪资（2026-10-20）：低价引流或单价不稳，只进边界
HOURLY_CAP = 200            # 时薪上限超过 200 元/时按可疑处理（2026-10-20 用户确认）
WORKDAYS_PER_MONTH = 22     # 行业惯例月工作日，元/月 → 元/天
DEFAULT_DAYS_PER_WEEK = 5   # 列表 daysPerWeekDesc 实测恒为空（160/160），周薪按 5 天折算
DEFAULT_INCLUDE = ["前端", "全栈", "客户端", "Electron", "React", "Node"]  # 岗位名门禁：开发词
DEFAULT_EXCLUDE = ["老师", "主播", "销售", "剪辑", "客服"]  # 2026-10-20：「远程办公」35 条里 33 条是这些

# 输出瘦身：内部字段 + 门禁后恒定的字段（deliveredBefore 全 False / jobValid 全 True），
# 减少模型上下文里的死重量
_SLIM_KEYS = ("securityId", "lid", "deliveredBefore", "jobValid")


def _slim(job: dict) -> dict:
    return {k: v for k, v in job.items() if k not in _SLIM_KEYS}


def convert_unit(sp: dict, hours_per_day: float, days_per_week: int) -> dict:
    """计件薪资折算出时薪/日薪区间（元）。K 月薪属全职口径，不折算，返回空 dict。"""
    unit, lo, hi = sp["unit"], sp["min"], sp["max"]
    if unit == "时":
        hlo, hhi = lo, hi
    elif unit == "天":
        hlo, hhi = lo / hours_per_day, hi / hours_per_day
    elif unit == "周":
        hlo, hhi = lo / days_per_week / hours_per_day, hi / days_per_week / hours_per_day
    elif unit == "月":
        hlo, hhi = (lo / WORKDAYS_PER_MONTH / hours_per_day, hi / WORKDAYS_PER_MONTH / hours_per_day)
    else:
        return {}
    return {"hourlyMin": round(hlo, 1), "hourlyMax": round(hhi, 1),
            "dayMin": round(hlo * hours_per_day, 1), "dayMax": round(hhi * hours_per_day, 1)}


def screen_jobs(jobs: list[dict], cfg: dict) -> tuple[list[dict], list[dict], list[dict], dict]:
    """纯函数：返回 (candidates, boundary, dropped, stats)。boundary 条目带 boundaryReasons，
    dropped 条目带 reason。cfg 需含 blacklistCompanies/blacklistKeywords/salaryFloorDay/
    hoursPerDay/jobType/city/includeTitleKeywords/excludeTitleKeywords。"""
    hpd = float(cfg["hoursPerDay"])
    floor_day = float(cfg["salaryFloorDay"]) if cfg.get("salaryFloorDay") is not None else None
    include = cfg.get("includeTitleKeywords") or []
    exclude = cfg.get("excludeTitleKeywords") or []
    parttime_mode = str(cfg.get("jobType", "") or "") == "1903"
    city_name = CITIES.get(str(cfg.get("city", "")), "")
    city_mode = bool(city_name) and str(cfg.get("city")) != "100010000"
    blacklist_companies = cfg.get("blacklistCompanies") or []
    blacklist_keywords = cfg.get("blacklistKeywords") or []

    candidates, boundary, dropped = [], [], []
    seen_company_job: set[tuple[str, str]] = set()
    stats: dict = {"input": len(jobs), "candidates": 0, "boundary": 0, "dropped": {}}

    def drop(job: dict, reason: str) -> None:
        dropped.append({"id": job.get("id"), "job": job.get("job"), "company": job.get("company"),
                        "salary": job.get("salary"), "reason": reason})
        stats["dropped"][reason.split(":")[0]] = stats["dropped"].get(reason.split(":")[0], 0) + 1

    for job in jobs:
        title = job.get("job") or ""
        if not job.get("jobValid", True):
            drop(job, "job_invalid")
            continue
        if job.get("deliveredBefore"):
            drop(job, "delivered_7d")
            continue
        if job.get("goldHunter"):
            drop(job, "hunter")
            continue
        if any(c and c in (job.get("company") or "") for c in blacklist_companies):
            drop(job, "blacklist_company")
            continue
        hay = " ".join(filter(None, [title, job.get("company"), job.get("industry"),
                                     " ".join(job.get("tags") or []), " ".join(job.get("skills") or [])]))
        hit = next((k for k in blacklist_keywords if k and k in hay), None)
        if hit:
            drop(job, f"blacklist_keyword:{hit}")
            continue
        if city_mode and city_name not in (job.get("area") or ""):
            drop(job, "city")
            continue
        # 兼职模式：响应 jobType=6 为兼职、0 为全职（见 references/boss-zhipin.md 已知怪癖 #3）
        if parttime_mode and job.get("jobType") is not None and str(job["jobType"]) != "6":
            drop(job, "not_parttime")
            continue
        ex_hit = next((k for k in exclude if k and k in title), None)
        if ex_hit:
            drop(job, f"title_excluded:{ex_hit}")
            continue
        if include and not any(k and k in title for k in include):
            drop(job, "title_not_dev")
            continue
        key = (job.get("company") or "", title)
        if key in seen_company_job:
            drop(job, "duplicate")
            continue
        seen_company_job.add(key)

        out = _slim(job)
        # 重新解析而非信任快照里的 salaryParsed：旧快照可能是残缺版本的解析结果
        # （2026-10-20 快照 160/160 为 null，修复 parse_salary 后老数据零成本复筛）
        sp = parse_salary(job.get("salary") or "") or job.get("salaryParsed")
        if sp and sp.get("unit") != "K":
            out["salaryParsed"] = sp
            dwm = re.search(r"(\d+)", job.get("daysPerWeek") or "")
            conv = convert_unit(sp, hpd, int(dwm.group(1)) if dwm else DEFAULT_DAYS_PER_WEEK)
            out.update(conv)
            reasons = []
            if floor_day is not None and conv["dayMax"] < floor_day * HARD_CUT:
                reasons.append("below_floor")
            if sp["max"] > 0 and sp["min"] / sp["max"] <= 1 / WIDE_RATIO:
                reasons.append("wide_range")
            if conv["hourlyMax"] > HOURLY_CAP:
                reasons.append("hourly_too_high")
            out["belowFloor"] = "below_floor" in reasons
            if reasons:
                out["boundaryReasons"] = reasons
                boundary.append(out)
                stats["boundary"] += 1
                continue
        candidates.append(out)
        stats["candidates"] += 1

    return candidates, boundary, dropped, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="岗位预过滤与薪资折算")
    parser.add_argument("--jobs", help="搜索快照路径（默认 BOSS_DIR 下最新 jobs-*.json）")
    parser.add_argument("--config-path", help="config 路径（默认 ~/.poseidon/outreach/config.json）")
    parser.add_argument("--out-dir", help="输出目录（默认 BOSS_DIR）")
    args = parser.parse_args()

    config_path = Path(args.config_path) if args.config_path else CONFIG_PATH
    raw_cfg = read_json(config_path, {})
    _, ignored = config_gaps(raw_cfg)
    for k in ignored:
        print(f"IGNORED {k}（列表接口没有活跃天数，该配置无效）")
    cfg = {**DEFAULT_CONFIG, **raw_cfg}
    for k, default in (("includeTitleKeywords", DEFAULT_INCLUDE), ("excludeTitleKeywords", DEFAULT_EXCLUDE)):
        cfg.setdefault(k, default)

    jobs_path = Path(args.jobs) if args.jobs else max(
        BOSS_DIR.glob("jobs-*.json"), key=lambda p: p.stat().st_mtime, default=None)
    if not jobs_path:
        print("NO_INPUT BOSS_DIR 下没有 jobs-*.json，请先运行 search.py")
        return 1
    payload = read_json(jobs_path, {})
    jobs = payload.get("jobs") or []
    if not jobs:
        print(f"NO_INPUT {jobs_path} 里没有 jobs")
        return 1

    unit_jobs = [j for j in jobs if (j.get("salaryParsed") or {}).get("unit") not in (None, "K")]
    needs = [k for k in ("hoursPerDay", "salaryFloorDay") if cfg.get(k) is None] if unit_jobs else []
    if needs:
        print(f"CONFIG_MISSING 缺少 {'、'.join(needs)}。计件薪资（{len(unit_jobs)} 条）必须折算，"
              "hoursPerDay 要问用户本人（不得默认 8 小时），补问后写入 config.json 再重跑")
        return 1

    candidates, boundary, dropped, stats = screen_jobs(jobs, cfg)
    date = (payload.get("fetchedAt") or time.strftime("%Y-%m-%d"))[:10]
    out_dir = Path(args.out_dir) if args.out_dir else BOSS_DIR
    ctx_cfg = {k: cfg.get(k) for k in ("jobType", "city", "salaryFloorDay", "hoursPerDay")}
    candidates_payload = {"source": str(jobs_path), "fetchedAt": payload.get("fetchedAt"),
                          "filteredAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "config": ctx_cfg,
                          **stats, "boundary": boundary, "candidates": candidates}
    candidates_path = out_dir / f"candidates-{date}.json"
    write_json(candidates_path, candidates_payload)
    screen_payload = {**candidates_payload, "dropped": dropped}
    screen_path = out_dir / f"screen-{date}.json"
    write_json(screen_path, screen_payload)

    print(f"[filter] 输入 {stats['input']} → 候选 {stats['candidates']} + 边界 {stats['boundary']}"
          f"，淘汰 {sum(stats['dropped'].values())}（{stats['dropped']}）")
    print(f"[filter] 候选/边界 → {candidates_path}；审计（含淘汰明细）→ {screen_path}")
    print(f"RESULT {candidates_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
