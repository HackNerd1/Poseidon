#!/usr/bin/env python3
"""Boss直聘岗位搜索与抓取（joblist.json 接口拦截版）。

原理：真实浏览器加载搜索页，SPA 自己请求 wapi/zpgeek/search/joblist.json（明文数据，
无字体反爬）；脚本用 expect_response 拦截响应取数。翻页 = 滚动到底触发无限加载
（URL 的 page 参数被 SPA 无视，勿用）。分页机制与字段见 references/boss-zhipin.md。

用法:
    python search.py --query "golang" [--city 101280600] [--pages 3] [--out jobs.json]
    python search.py --config            # 按 ~/.poseidon/outreach/config.json 逐关键词搜索

输出: 岗位 JSON 文件；同日重跑自动把同名旧快照轮转为 -HHMM 后缀，不覆盖
stdout 末行: RESULT <路径> stopped=<none|captcha|blank|no_api|daily_limit> fetched=<条数>
退出码: 0 成功 / 2 未登录 / 1 风控或抓取失败或配置缺字段

--config 前置校验（config_gaps）：缺 headed / 兼职缺 hoursPerDay、salaryFloorDay 时打印
CONFIG_MISSING 拒绝搜索——这些字段必须问用户本人，不能默认值蒙混（headed=false 会掩盖旧配置缺字段，
hoursPerDay 默认 8 小时曾被用户明确纠正）。残留的死配置（skipInactiveDays）打印 IGNORED 后忽略。
"""
import argparse
import random
import sys
import time

from _lib import (BOSS_DIR, CITIES, CONFIG_PATH, DEFAULT_CONFIG, config_gaps,
                  delivered_recently, first_page, goto_guarded, has_login, is_captcha,
                  is_daily_limit, launch, parse_salary, rand_delay, read_json,
                  record_session, rotate_existing, shot, sync_pw, write_json)

JOBLIST = "joblist.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Boss直聘岗位搜索")
    parser.add_argument("--query", help="搜索关键词")
    parser.add_argument("--city", help="城市代码（默认取 config）")
    parser.add_argument("--pages", type=int, help="每个关键词加载页数（每页 15 条）")
    parser.add_argument("--out", help="输出 JSON 路径")
    parser.add_argument("--config", action="store_true", help="使用 config.json 的 keywords")
    parser.add_argument("--job-type", dest="job_type", help="招聘类型筛选（1903=兼职），默认取 config.jobType")
    parser.add_argument("--headed", action="store_true", help="前台显示浏览器窗口（默认隐藏窗口后台运行；后台触发风控时加此参数重试）")
    args = parser.parse_args()
    raw_config = read_json(CONFIG_PATH, {})
    missing, ignored = config_gaps(raw_config)
    config = {**DEFAULT_CONFIG, **raw_config}
    queries = config["keywords"] if args.config else ([args.query] if args.query else [])
    if not queries:
        parser.error("缺少 --query，或 --config 且 config.json 配置了 keywords")
    return argparse.Namespace(
        queries=queries,
        city=args.city or str(config["city"]),
        job_type=str(args.job_type if args.job_type is not None else config.get("jobType", "") or ""),
        pages=args.pages or config["pages"],
        out=args.out or str(BOSS_DIR / f"jobs-{time.strftime('%Y-%m-%d')}.json"),
        headed=args.headed or bool(config.get("headed")),
        # 只在 --config 模式强制：临时单关键词搜索不依赖用户偏好字段
        missing_required=missing if args.config else [],
        ignored_keys=ignored,
    )


def map_job(raw: dict, query: str) -> dict:
    """jobList 原始字段 → 统一岗位 schema。"""
    jid = raw.get("encryptJobId") or ""
    online = bool(raw.get("bossOnline"))
    return {
        "id": jid,
        "link": f"https://www.zhipin.com/job_detail/{jid}.html",
        "job": raw.get("jobName") or "",
        "salary": raw.get("salaryDesc") or "",
        "salaryParsed": parse_salary(raw.get("salaryDesc") or ""),
        "company": raw.get("brandName") or "",
        "area": "·".join(filter(None, [raw.get("cityName"), raw.get("areaDistrict"),
                                       raw.get("businessDistrict")])),
        "hr": raw.get("bossName") or "",
        "hrTitle": raw.get("bossTitle") or "",
        "hrOnline": online,
        "goldHunter": bool(raw.get("goldHunter")),
        "tags": [t for t in (raw.get("jobLabels") or []) if t],
        "skills": [t for t in (raw.get("skills") or []) if t],
        "welfare": [t for t in (raw.get("welfareList") or []) if t],
        "experience": raw.get("jobExperience") or "",
        "degree": raw.get("jobDegree") or "",
        "industry": raw.get("brandIndustry") or "",
        "scale": raw.get("brandScaleName") or "",
        "stage": raw.get("brandStageName") or "",
        "jobType": raw.get("jobType"),
        "daysPerWeek": raw.get("daysPerWeekDesc") or "",
        "leastMonth": raw.get("leastMonthDesc") or "",
        "securityId": raw.get("securityId") or "",
        "lid": raw.get("lid") or "",
        "jobValid": raw.get("jobValidStatus") == 1,
        "query": query,
        "deliveredBefore": delivered_recently(jid),
    }


def main() -> int:
    args = parse_args()
    for k in args.ignored_keys:
        print(f"IGNORED {k}（列表接口没有活跃天数，该配置无效）")
    if args.missing_required:
        print(f"CONFIG_MISSING 缺少配置字段: {'、'.join(args.missing_required)}。"
              "这些字段必须问用户本人后写入 config.json 再重试（headed 后台/前台、"
              "兼职的 hoursPerDay 每天工时不得默认 8、salaryFloorDay 日薪下限）")
        return 1
    with sync_pw() as pw:
        ctx = launch(pw, visible=args.headed)
        try:
            record_session("search")  # 一次进程一条，翻页不再累加
            page = first_page(ctx)
            if not has_login(ctx):
                print("LOGIN_EXPIRED 登录态缺失，请先运行: python login.py")
                return 2

            all_jobs: dict[str, dict] = {}
            stopped = None

            for query in args.queries:
                url = (f"https://www.zhipin.com/web/geek/job"
                       f"?query={query}&city={args.city}"
                       + (f"&jobType={args.job_type}" if args.job_type else ""))
                print(f"[search] {query}: {url}")

                # 首屏：拦截 SPA 自己发起的 joblist POST
                # 有头模式等待更长：出现图形验证码时人工可在窗口里过验
                def is_joblist(r):
                    return JOBLIST in r.url and r.request.method == "POST"
                api_timeout = 180_000 if args.headed else 30_000
                try:
                    with page.expect_response(is_joblist, timeout=api_timeout) as ri:
                        diag = goto_guarded(page, url)
                    if diag:
                        if not args.headed:
                            diag += "（当前是屏幕外有头窗口。可加 --headed 在前台人工过验后重试）"
                        print(f"RISK_BLANK {diag}")
                        stopped = "blank"
                        break
                except Exception:
                    shot(page, "search-no-api")
                    if is_captcha(page):
                        hint = "请运行 search.py --headed 在窗口中人工完成图形验证后重试；" \
                               "频繁出现则降低频次冷却几分钟" 
                        print(f"CAPTCHA 搜索页触发安全验证（{hint}），截图已存")
                        stopped = "captcha"
                    else:
                        hint = "；可加 --headed 重试" if not args.headed else ""
                        print(f"未拦截到 joblist.json（可能未登录/风控/改版）{hint}，截图已存")
                        stopped = "no_api"
                    break

                if is_captcha(page):
                    shot(page, "search-captcha")
                    print("CAPTCHA 触发安全验证，需人工处理（见 screenshots/）")
                    stopped = "captcha"
                    break

                for p in range(1, args.pages + 1):
                    try:
                        data = ri.value.json()
                    except Exception:
                        shot(page, "search-body-lost")
                        hint = "" if args.headed else "（可加 --headed 重试）"
                        print(f"RISK_BLANK 数据响应体被页面跳转销毁（风控/加载异常）{hint}，截图已存")
                        stopped = "blank"
                        break
                    zp = data.get("zpData", {})
                    raw_jobs = zp.get("jobList") or []
                    fresh = 0
                    for raw in raw_jobs:
                        job = map_job(raw, query)
                        if job["id"] and job["id"] not in all_jobs:
                            all_jobs[job["id"]] = job
                            fresh += 1
                    print(f"[search] 第{p}批 {len(raw_jobs)} 条，新增 {fresh}，累计 {len(all_jobs)}")

                    if not zp.get("hasMore", True) or p >= args.pages:
                        break

                    # 滚动到底触发下一批（SPA 无限加载）
                    try:
                        with page.expect_response(is_joblist, timeout=12_000) as ri_next:
                            for _ in range(8):
                                page.mouse.wheel(0, random.randint(500, 900))
                                rand_delay((0.3, 0.7))
                        ri = ri_next
                    except Exception:
                        print("[search] 滚动后无更多数据")
                        break
                    rand_delay((2, 4))

                if stopped:
                    break
                rand_delay((2, 5))

            if is_daily_limit(page):
                print("DAILY_LIMIT 今日沟通已达平台上限")
                stopped = "daily_limit"

            jobs_list = list(all_jobs.values())
            payload = {
                "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "city": args.city,
                "jobType": args.job_type,
                "cityName": CITIES.get(args.city, args.city),
                "query": args.queries,
                "pages": args.pages,
                "count": len(jobs_list),
                "stopped": stopped,
                "jobs": jobs_list,
            }
            rotated = rotate_existing(args.out)
            if rotated:
                print(f"[search] 同名旧快照已轮转 → {rotated}（同日重跑不覆盖）")
            write_json(args.out, payload)
            print(f"[search] 共 {len(jobs_list)} 条 → {args.out}")
            print(f"RESULT {args.out} stopped={stopped or 'none'} fetched={len(jobs_list)}")
            return 0 if jobs_list else 1
        finally:
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
