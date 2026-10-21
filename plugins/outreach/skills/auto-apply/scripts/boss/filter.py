#!/usr/bin/env python3
"""岗位预过滤：把搜索快照压成小而干净的候选集。薪资折算、岗位名门禁、去重在此完成，
模型只对剩余项打分，不再逐条读原始 JSON 心算薪资。

为什么放脚本侧（2026-10-20 实测）：160 条原始岗位整份进上下文是最大 token 消耗点；
且当时 parse_salary 对兼职四类单位全返回 null，硬过滤形同虚设，靠模型对话里临时脚本补。

用法:
    python filter.py --show-config          # 打印当前配置与折算公式，不读 jobs
    python filter.py --show-config --ack    # 用户确认后写入 confirmedAt（不得代确认）
    python filter.py --plan-target 10       # 按今日目标条数给建议抓取页数
    python filter.py --table                # 最新 jobs-*.json，stdout 紧凑评分表
    python filter.py --table --merge-rounds # 合并同日 jobs-<日期>*.json，按岗位 id 去重
    python filter.py --jobs jobs-2026-10-20.json [--config-path config.json]

输出（BOSS_DIR 下，日期取 jobs 快照的 fetchedAt）:
    candidates-<日期>.json   # 候选 + 边界（写计划/复核时按 id 取字段用）
    screen-<日期>.json       # 全量审计：每条的去向与原因、淘汰统计，调阈值时才读
同日重跑自动把同名旧文件轮转为 -HHMM 后缀，不覆盖（2026-10-20 screen 审计曾被覆盖）。
已抓过详情（detail-<id>.json）的岗位会带上 deadline/hrActivity/workCycle/jdFlags。
stdout 末行: RESULT <candidates路径>；跨轮时另有 ROUND 行
退出码: 0 成功 / 1 输入缺失或配置不足（CONFIG_MISSING 需补问用户，不得用默认值折算）
"""
import argparse
import math
import re
import sys
import time
from pathlib import Path

from _lib import (BOSS_DIR, CITIES, CONFIG_PATH, DEFAULT_CONFIG, config_gaps,
                  deadline_expired, hr_long_inactive, parse_salary, read_json,
                  rotate_existing, scan_jd_flags, write_json)

# 折算常量与依据：
HARD_CUT = 0.85             # matching.md：上限低于期望下限的 85% 才算硬伤，留 15% 谈判空间
WIDE_RATIO = 3.0            # 上限/下限 ≥ 3 的宽幅薪资（2026-10-20）：低价引流或单价不稳，只进边界
HOURLY_CAP = 200            # 时薪上限超过 200 元/时按可疑处理（2026-10-20 用户确认）
WORKDAYS_PER_MONTH = 22     # 行业惯例月工作日。不用 21.75：与日/时薪差约 1%，below_floor 走同一条 convert_unit
DEFAULT_DAYS_PER_WEEK = 5   # 列表 daysPerWeekDesc 实测恒为空（160/160），周薪按 5 天折算
ABANDON_DAY_MAX = 150       # below_floor 且日上限低于此值：建议放弃，默认不进 stdout 表（2026-10-21）
VIABLE_RATE = 0.06          # 2026-10-21 实测：118 抓取 → 7 可投（详情复核前）。只用于规划页数
PAGE_SIZE = 15
DEFAULT_INCLUDE = ["前端", "全栈", "客户端", "Electron", "React", "Node"]  # 岗位名门禁：开发词
DEFAULT_EXCLUDE = ["老师", "主播", "销售", "剪辑", "客服"]  # 2026-10-20：「远程办公」35 条里 33 条是这些
# 列表学历档。学历不限不进表。岗位要求高于 config.degreeFloor 时打标，不静默淘汰。
DEGREE_RANK = {"高中": 1, "中专": 1, "大专": 2, "本科": 3, "硕士": 4, "博士": 5}

# 输出瘦身：内部字段 + 门禁后恒定的字段（deliveredBefore 全 False / jobValid 全 True），
# 减少模型上下文里的死重量
_SLIM_KEYS = ("securityId", "lid", "deliveredBefore", "jobValid")


def _slim(job: dict) -> dict:
    return {k: v for k, v in job.items() if k not in _SLIM_KEYS}


def degree_rank(text: str) -> int | None:
    """学历要求 → 档位。不限/空返回 None（不打标）。"""
    text = text or ""
    if not text or "不限" in text:
        return None
    for name, rank in DEGREE_RANK.items():
        if name in text:
            return rank
    return None


def parse_exp_range(text: str) -> tuple[int, int] | None:
    """「3-5年 / 5-10年 / 10年以上 / 1年以内 / 应届」→ (min, max)。不限返回 None。"""
    text = text or ""
    if not text or "不限" in text:
        return None
    if "应届" in text or "在校" in text:
        return (0, 0)
    m = re.search(r"(\d+)\s*-\s*(\d+)", text)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.search(r"(\d+)\s*年以上", text)
    if m:
        return (int(m.group(1)), 99)
    m = re.search(r"(\d+)\s*年以内", text)
    if m:
        return (0, int(m.group(1)))
    return None


def list_rule_flags(job: dict, cfg: dict) -> list[str]:
    """列表字段就能定的硬标。打标不淘汰——年限差一两年、硕士岗仍可能谈。"""
    flags: list[str] = []
    floor = cfg.get("degreeFloor")
    if floor:
        job_rank = degree_rank(job.get("degree") or "")
        floor_rank = degree_rank(str(floor))
        if job_rank is not None and floor_rank is not None and job_rank > floor_rank:
            flags.append("degree_above")
    years = cfg.get("experienceYears")
    if years is not None:
        rng = parse_exp_range(job.get("experience") or "")
        if rng:
            lo, hi = rng
            if float(years) < lo:
                flags.append("exp_short")
            elif hi < float(years) and hi <= 1:
                flags.append("exp_over")
    return flags


def load_detail_marks(out_dir: Path) -> dict[str, dict]:
    """收集已抓详情。无 jdFlags 字段的旧文件按全文重扫，不必为打标重开浏览器。"""
    known: dict[str, dict] = {}
    for pf in out_dir.glob("detail-*.json"):
        d = read_json(pf, {})
        jid = str(d.get("id") or "")
        if not jid:
            continue
        terms = d.get("terms") or {}
        deadline = terms.get("招聘截止") or ""
        # 优先 JD 正文。侧栏推荐岗在 rawText 里，不能和正文拼在一起扫
        blob = (d.get("jdText") or "").strip() or (d.get("rawText") or "")
        known[jid] = {
            "deadline": deadline,
            "expired": deadline_expired(deadline) if deadline else None,
            "hrActivity": d.get("hrActivity") or "",
            "workCycle": terms.get("每周工期") or terms.get("工作周期") or "",
            "jdFlags": scan_jd_flags(blob, terms),
        }
    return known


def load_deadlines(out_dir: Path) -> dict[str, dict]:
    """兼容旧名。新代码用 load_detail_marks。"""
    return load_detail_marks(out_dir)


def apply_detail_marks(out: dict, info: dict | None) -> None:
    """把详情标写进候选。边界岗也要写——低价岗同样可能是死岗。"""
    if not info:
        return
    if info.get("deadline"):
        out["deadline"] = info["deadline"]
    if info.get("expired"):
        out["deadlineExpired"] = True
    if info.get("hrActivity"):
        out["hrActivity"] = info["hrActivity"]
    if info.get("workCycle"):
        out["workCycle"] = info["workCycle"]
    flags = list(out.get("ruleFlags") or [])
    for flag in info.get("jdFlags") or []:
        if flag not in flags:
            flags.append(flag)
    if info.get("expired") and hr_long_inactive(info.get("hrActivity") or ""):
        if "dead_post" not in flags:
            flags.append("dead_post")
    if flags:
        out["ruleFlags"] = flags


def grade_boundary(boundary: list[dict], boundary_min: float) -> tuple[list[dict], list[dict]]:
    """below_floor 且日上限 < boundary_min → 建议放弃。其余边界值得看。"""
    review, abandon = [], []
    for job in boundary:
        reasons = job.get("boundaryReasons") or []
        day_max = job.get("dayMax")
        if "below_floor" in reasons and day_max is not None and day_max < boundary_min:
            job["boundaryGrade"] = "abandon"
            abandon.append(job)
        else:
            job["boundaryGrade"] = "review"
            review.append(job)
    return review, abandon


def _flag_cells(job: dict) -> str:
    flags = list(job.get("boundaryReasons") or [])
    if job.get("belowFloor") and "below_floor" not in flags:
        flags.append("below_floor")
    if job.get("nearFloor") and "near_floor" not in flags:
        flags.append("near_floor")
    if job.get("deadlineExpired") and "deadline_expired" not in flags:
        flags.append("deadline_expired")
    for flag in job.get("ruleFlags") or []:
        if flag not in flags:
            flags.append(flag)
    return ",".join(flags)


def render_table(candidates: list[dict], boundary: list[dict],
                 new_ids: set[str] | None = None) -> str:
    """紧凑评分视图（TSV，候选在前边界在后）。工作周期无详情时为 '-'，避免空列误导。"""
    cols = ["#", "状态", "本轮", "id", "岗位", "公司", "薪资", "area", "hrOnline", "工作周期",
            "经验", "学历", "行业", "阶段", "规模", "技能", "标记"]
    lines = ["\t".join(cols)]
    rows = [("候选", j) for j in candidates] + [("边界", j) for j in boundary]
    for i, (status, j) in enumerate(rows, 1):
        if new_ids is None:
            round_cell = "-"
        else:
            round_cell = "new" if j.get("id") in new_ids else "seen"
        cycle = j.get("workCycle") or j.get("daysPerWeek") or "-"
        cells = [str(i), status, round_cell, j.get("id") or "", j.get("job") or "",
                 j.get("company") or "", j.get("salary") or "", j.get("area") or "",
                 "true" if j.get("hrOnline") else "", cycle,
                 j.get("experience") or "", j.get("degree") or "",
                 j.get("industry") or "", j.get("stage") or "", j.get("scale") or "",
                 ",".join(j.get("skills") or []), _flag_cells(j)]
        lines.append("\t".join(cells))
    return "\n".join(lines)


def convert_unit(sp: dict, hours_per_day: float, days_per_week: int) -> dict:
    """计件薪资折算出时薪/日薪区间（元）。K 月薪属全职口径，不折算，返回空 dict。

    日/周/月的 hoursPerDay 在折算中抵消，日收入只取决于标价与工作日；
    时薪才乘 hoursPerDay。月/日/时的 below_floor 都比较 dayMax，不另设月薪线。
    """
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


def jobs_day(path: Path) -> str:
    m = re.match(r"jobs-(\d{4}-\d{2}-\d{2})", path.name)
    return m.group(1) if m else ""


def merge_round_jobs(primary: Path) -> tuple[list[dict], dict]:
    """合并同日 jobs-<日期>*.json，按岗位 id 去重。primary 里未在其他快照出现的 id 为本轮新增。"""
    day = jobs_day(primary)
    files = sorted(primary.parent.glob(f"jobs-{day}*.json"), key=lambda p: p.stat().st_mtime) if day else [primary]
    if primary not in files and primary.exists():
        files.append(primary)
    seen_prior: set[str] = set()
    by_id: dict[str, dict] = {}
    primary_resolved = primary.resolve()
    for path in files:
        if path.resolve() == primary_resolved:
            continue
        for job in read_json(path, {}).get("jobs") or []:
            jid = job.get("id")
            if not jid:
                continue
            seen_prior.add(jid)
            by_id[jid] = job
    primary_ids: set[str] = set()
    for job in read_json(primary, {}).get("jobs") or []:
        jid = job.get("id")
        if not jid:
            continue
        by_id[jid] = job  # 本轮字段覆盖旧快照
        primary_ids.add(jid)
    new_ids = primary_ids - seen_prior
    return list(by_id.values()), {
        "files": len(files),
        "unique": len(by_id),
        "overlap": len(primary_ids & seen_prior),
        "new_ids": new_ids,
    }


def screen_jobs(jobs: list[dict], cfg: dict, known_details: dict[str, dict] | None = None
                ) -> tuple[list[dict], list[dict], list[dict], dict]:
    """纯函数：返回 (candidates, boundary, dropped, stats)。boundary 条目带 boundaryReasons，
    dropped 条目带 reason。cfg 需含 blacklistCompanies/blacklistKeywords/salaryFloorDay/
    hoursPerDay/jobType/city/includeTitleKeywords/excludeTitleKeywords。
    known_details 为 load_detail_marks() 的结果。"""
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
        flags = list_rule_flags(job, cfg)
        if flags:
            out["ruleFlags"] = flags
        # 重新解析而非信任快照里的 salaryParsed：旧快照可能是残缺版本的解析结果
        # （2026-10-20 快照 160/160 为 null，修复 parse_salary 后老数据零成本复筛）
        sp = parse_salary(job.get("salary") or "") or job.get("salaryParsed")
        reasons: list[str] = []
        if sp and sp.get("unit") != "K":
            out["salaryParsed"] = sp
            dwm = re.search(r"(\d+)", job.get("daysPerWeek") or "")
            conv = convert_unit(sp, hpd, int(dwm.group(1)) if dwm else DEFAULT_DAYS_PER_WEEK)
            out.update(conv)
            if floor_day is not None and conv["dayMax"] < floor_day * HARD_CUT:
                reasons.append("below_floor")
            elif floor_day is not None and conv["dayMax"] < floor_day:
                # 贴线：在 85% 硬切之上、期望下限之下。不进边界，只打标（2026-10-21 法研堂）
                out["nearFloor"] = True
            if sp["max"] > 0 and sp["min"] / sp["max"] <= 1 / WIDE_RATIO:
                reasons.append("wide_range")
            if conv["hourlyMax"] > HOURLY_CAP:
                reasons.append("hourly_too_high")
            out["belowFloor"] = "below_floor" in reasons
        apply_detail_marks(out, (known_details or {}).get(job.get("id") or ""))
        if reasons:
            out["boundaryReasons"] = reasons
            boundary.append(out)
            stats["boundary"] += 1
            continue
        candidates.append(out)
        stats["candidates"] += 1

    return candidates, boundary, dropped, stats


def format_config_confirm(cfg: dict) -> str:
    """启动确认块：关键字段 + 与 convert_unit 相同的折算公式。只读。"""
    hpd = cfg.get("hoursPerDay")
    floor = cfg.get("salaryFloorDay")
    city = str(cfg.get("city") or "")
    lines = [
        "CONFIG_CONFIRM",
        f"headed={cfg.get('headed', '<unset>')}",
        f"jobType={cfg.get('jobType') or '<全部>'}",
        f"keywords={','.join(cfg.get('keywords') or []) or '<unset>'}",
        f"city={city} ({CITIES.get(city, city or '<unset>')})",
        f"pages={cfg.get('pages', '<unset>')}",
        f"dailyLimit={cfg.get('dailyLimit', '<unset>')}",
        f"hoursPerDay={hpd if hpd is not None else '<unset>'}（每天实际工时；必须用户本人确认，不得默认 8）",
        f"salaryFloorDay={floor if floor is not None else '<unset>'}",
        f"experienceYears={cfg.get('experienceYears', '<unset>')}",
        f"degreeFloor={cfg.get('degreeFloor') or '<unset>'}（未设置则列表级学历不打标）",
        "折算（与 filter.py convert_unit 同一套，不要另心算）:",
        "  时薪 × hoursPerDay = 日薪",
        "  日薪 = 标价",
        f"  周薪 ÷ {DEFAULT_DAYS_PER_WEEK} = 日薪",
        f"  月薪 ÷ {WORKDAYS_PER_MONTH} = 日薪（与日/时薪比较同一个 dayMax；22 是行业惯例月工作日，不是 21.75）",
    ]
    if floor is not None:
        cut = float(floor) * HARD_CUT
        lines.append(f"  below_floor: 日上限 < {floor}×{HARD_CUT:g} = {cut:g}")
        lines.append(f"  near_floor: 日上限 ∈ [{cut:g}, {floor}) 标贴线，仍留候选")
    else:
        lines.append("  below_floor: 缺 salaryFloorDay，无法算硬切线")
    lines.append(f"  hourly_too_high: 时薪上限 > {HOURLY_CAP}")
    lines.append(f"  建议放弃: below_floor 且日上限 < {ABANDON_DAY_MAX}（--boundary-min 0 展开）")
    lines.append("请确认或调整上述字段后再搜索。用户明确确认后才加 --ack；不得代确认。")
    return "\n".join(lines)


def plan_target(target: int, keywords: int, already: int = 0) -> dict:
    """按详情前转化率估算还要抓多少。不启动浏览器，也不保证详情复核后仍够 N。"""
    need = math.ceil(target / VIABLE_RATE) if target > 0 else 0
    remain = max(0, need - max(already, 0))
    kw = max(int(keywords or 1), 1)
    pages = math.ceil(remain / (PAGE_SIZE * kw)) if remain else 0
    return {"target": target, "viable_rate": VIABLE_RATE, "fetched_needed": need,
            "already": already, "keywords": kw, "pages_suggest": pages}


def format_target_plan(plan: dict) -> str:
    return (f"TARGET_PLAN target={plan['target']} viable_rate={plan['viable_rate']} "
            f"fetched_needed={plan['fetched_needed']} already={plan['already']} "
            f"pages_suggest={plan['pages_suggest']} keywords={plan['keywords']} "
            "note=规划用详情前转化；达标即停，不超额投，频控红线不变")


def _latest_jobs() -> Path | None:
    found = list(BOSS_DIR.glob("jobs-*.json"))
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)


def main() -> int:
    parser = argparse.ArgumentParser(description="岗位预过滤与薪资折算")
    parser.add_argument("--jobs", help="搜索快照路径（默认 BOSS_DIR 下最新 jobs-*.json）")
    parser.add_argument("--config-path", help="config 路径（默认 ~/.poseidon/outreach/config.json）")
    parser.add_argument("--out-dir", help="输出目录（默认 BOSS_DIR）")
    parser.add_argument("--table", action="store_true",
                        help="stdout 追加打印紧凑评分表（评分读表，不读 candidates JSON）")
    parser.add_argument("--merge-rounds", action="store_true",
                        help="合并同日 jobs-<日期>*.json，按岗位 id 去重，并打印 ROUND 行")
    parser.add_argument("--new-only", action="store_true",
                        help="配合 --merge-rounds：stdout 表只列本轮新增（JSON 仍含全量）")
    parser.add_argument("--boundary-min", type=float, default=ABANDON_DAY_MAX,
                        help="below_floor 日上限低于此值归建议放弃，不进 stdout 表（0=全部展开）")
    parser.add_argument("--show-config", action="store_true", help="打印配置与折算公式，不启动浏览器")
    parser.add_argument("--ack", action="store_true", help="用户确认配置后写入 confirmedAt。不得在确认前使用")
    parser.add_argument("--plan-target", type=int, help="今日目标投递条数，打印建议抓取量")
    parser.add_argument("--already", type=int, default=0, help="本目标下已抓取条数，配合 --plan-target")
    args = parser.parse_args()

    config_path = Path(args.config_path) if args.config_path else CONFIG_PATH
    raw_cfg = read_json(config_path, {})
    missing, ignored = config_gaps(raw_cfg)
    if args.show_config or args.ack:
        print(format_config_confirm({**DEFAULT_CONFIG, **raw_cfg}))
        for k in ignored:
            print(f"IGNORED {k}（列表接口没有活跃天数，该配置无效）")
        if missing:
            print(f"CONFIG_MISSING 缺少 {'、'.join(missing)}。先补问写回，hoursPerDay 不得默认 8")
    if args.ack:
        if not raw_cfg:
            print(f"CONFIG_MISSING 没有可读的 config: {config_path}")
            return 1
        if missing:
            print("CONFIG_ACK_REFUSED 缺字段时不写 confirmedAt")
            return 1
        raw_cfg["confirmedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        write_json(config_path, raw_cfg)
        print(f"CONFIG_ACK {raw_cfg['confirmedAt']}")
    if args.plan_target is not None:
        plan = plan_target(args.plan_target, len(raw_cfg.get("keywords") or []), args.already)
        print(format_target_plan(plan))
    confirm_only = (args.show_config or args.ack or args.plan_target is not None) and not (
        args.table or args.jobs or args.merge_rounds)
    if confirm_only:
        return 1 if missing else 0

    for k in ignored:
        if not (args.show_config or args.ack):
            print(f"IGNORED {k}（列表接口没有活跃天数，该配置无效）")
    cfg = {**DEFAULT_CONFIG, **raw_cfg}
    for k, default in (("includeTitleKeywords", DEFAULT_INCLUDE), ("excludeTitleKeywords", DEFAULT_EXCLUDE)):
        cfg.setdefault(k, default)

    jobs_path = Path(args.jobs) if args.jobs else _latest_jobs()
    if not jobs_path:
        print("NO_INPUT BOSS_DIR 下没有 jobs-*.json，请先运行 search.py")
        return 1
    payload = read_json(jobs_path, {})
    round_meta = None
    if args.merge_rounds:
        jobs, round_meta = merge_round_jobs(jobs_path)
    else:
        jobs = payload.get("jobs") or []
    if not jobs:
        print(f"NO_INPUT {jobs_path} 里没有 jobs")
        return 1

    unit_jobs = [j for j in jobs if (j.get("salaryParsed") or {}).get("unit") not in (None, "K")]
    # 合并后的旧快照可能 salaryParsed 残缺，再按原文扫一遍计件
    if not unit_jobs:
        unit_jobs = [j for j in jobs if parse_salary(j.get("salary") or "")
                     and parse_salary(j.get("salary") or "").get("unit") != "K"]
    needs = [k for k in ("hoursPerDay", "salaryFloorDay") if cfg.get(k) is None] if unit_jobs else []
    if needs:
        print(f"CONFIG_MISSING 缺少 {'、'.join(needs)}。计件薪资（{len(unit_jobs)} 条）必须折算，"
              "hoursPerDay 要问用户本人（不得默认 8 小时），补问后写入 config.json 再重跑")
        return 1

    out_dir = Path(args.out_dir) if args.out_dir else BOSS_DIR
    known = load_detail_marks(BOSS_DIR)  # detail.py 固定写 BOSS_DIR
    candidates, boundary, dropped, stats = screen_jobs(jobs, cfg, known_details=known)
    review, abandon = grade_boundary(boundary, args.boundary_min)
    date = (payload.get("fetchedAt") or time.strftime("%Y-%m-%d"))[:10]
    ctx_cfg = {k: cfg.get(k) for k in ("jobType", "city", "salaryFloorDay", "hoursPerDay",
                                       "degreeFloor", "experienceYears")}
    new_ids = round_meta["new_ids"] if round_meta else None
    candidates_payload = {"source": str(jobs_path), "fetchedAt": payload.get("fetchedAt"),
                          "filteredAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "config": ctx_cfg,
                          **stats, "abandon": len(abandon), "boundaryReview": len(review),
                          "boundary": boundary, "candidates": candidates}
    candidates_path = out_dir / f"candidates-{date}.json"
    rotated = rotate_existing(candidates_path)
    if rotated:
        print(f"[filter] 同名旧文件已轮转 → {rotated}（同日重跑不覆盖）")
    write_json(candidates_path, candidates_payload)
    screen_payload = {**candidates_payload, "dropped": dropped}
    screen_path = out_dir / f"screen-{date}.json"
    rotate_existing(screen_path)
    write_json(screen_path, screen_payload)

    print(f"[filter] 输入 {stats['input']} → 候选 {stats['candidates']} + 边界 {stats['boundary']}"
          f"（值得看 {len(review)}，建议放弃 {len(abandon)}），淘汰 {sum(stats['dropped'].values())}"
          f"（{stats['dropped']}）")
    if abandon:
        print(f"[filter] ABANDON {len(abandon)} 条 below_floor 且日上限 < {args.boundary_min:g}，"
              "未进 stdout 表；--boundary-min 0 展开")
    expired = [j for j in candidates + boundary if j.get("deadlineExpired")]
    if expired:
        print(f"[filter] DEADLINE_EXPIRED {len(expired)} 条招聘截止已过（已打 deadlineExpired 标，"
              "处置惯例见 references/matching.md：HR 长期不活跃才淘汰，近期活跃交用户决策）")
    dead = [j for j in candidates + boundary if "dead_post" in (j.get("ruleFlags") or [])]
    if dead:
        print(f"[filter] DEAD_POST {len(dead)} 条截止过期且 HR 长期不活跃，不要放进推荐")
    if round_meta:
        new_c = sum(1 for j in candidates if j.get("id") in new_ids)
        new_b = sum(1 for j in review if j.get("id") in new_ids)
        print(f"ROUND new_candidates={new_c} new_boundary={new_b} overlap={round_meta['overlap']} "
              f"files={round_meta['files']} unique={round_meta['unique']}")
    if args.table:
        show_c, show_b = candidates, review
        if args.new_only and new_ids is not None:
            show_c = [j for j in candidates if j.get("id") in new_ids]
            show_b = [j for j in review if j.get("id") in new_ids]
            print(f"[filter] NEW_ONLY 表内新增候选 {len(show_c)} + 边界 {len(show_b)}，"
                  f"已见 {stats['candidates'] + len(review) - len(show_c) - len(show_b)} 条不重复出表")
        print(render_table(show_c, show_b, new_ids))
    print(f"[filter] 候选/边界 → {candidates_path}；审计（含淘汰明细）→ {screen_path}")
    print(f"RESULT {candidates_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
