"""remotecn.com 岗位搜索（直连公开 API，只查不落盘）。

连接手册: ../../references/remotecn.md（端点/参数/怪癖/降级策略）。

用法:
  search.py --keyword "前端"                          # 服务端关键词搜索（中文自动编码）
  search.py --keyword "python" --work-type parttime --region CN
  search.py --keyword "全栈" --days 14 --limit 30     # datePosted 最近 N 天（本地过滤）
  search.py --latest                                  # 最新岗位流（不传关键词）
stdout 末行: RESULT matched=<本地行数> total=<服务端命中> pages=<拉取页数> stopped=<none|fetch_error>
退出码: 0 正常; 2 参数错误; 3 API 不可达/结构变更

服务端参数实测（2026-11-11）: keyword 支持中文子串匹配；workType=fulltime|parttime；
regionLimit=CN|worldwide|EU；sort=datePosted 默认降序；无日期过滤参数，--days 在本地过滤。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

API_BASE = os.environ.get("REMOTECN_API", "https://remotecn.com/api/jobs")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
PAGE_SIZE = 50  # 服务端实测支持；分页拉到凑满 limit 或翻完命中


def api_get(params: dict, timeout: int = 30, attempts: int = 3) -> dict:
    qs = urllib.parse.urlencode(params)
    url = f"{API_BASE}?{qs}"
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            last = e
            if i < attempts - 1:
                time.sleep(2 * (i + 1))
    print(f"FETCH_ERROR GET {url} 失败: {last}", file=sys.stderr)
    sys.exit(3)


def fetch_all(params: dict, limit: int) -> tuple[list[dict], int, int]:
    """按分页拉取直到凑满 limit 或翻完服务端命中。返回 (jobs, total, pages)。"""
    jobs: list[dict] = []
    total = 0
    page = 1
    while True:
        data = api_get({**params, "page": page, "limit": PAGE_SIZE})
        rows = data.get("data")
        if not isinstance(rows, list):
            print(f"FETCH_ERROR 响应结构变更: keys={list(data.keys())}", file=sys.stderr)
            sys.exit(3)
        total = (data.get("pagination") or {}).get("total", total)
        jobs.extend(rows)
        if len(rows) < PAGE_SIZE or len(jobs) >= total or len(jobs) >= limit * 2:
            break
        page += 1
    return jobs, total, page


def main() -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--keyword", action="append", default=[], help="服务端关键词，可传多次（OR 语义需多次调用）")
    ap.add_argument("--work-type", choices=["fulltime", "parttime"])
    ap.add_argument("--region", choices=["CN", "worldwide", "EU"])
    ap.add_argument("--days", type=int, help="只要 datePosted 最近 N 天（本地过滤）")
    ap.add_argument("--limit", type=int, default=50, help="出表条数上限（默认 50）")
    ap.add_argument("--latest", action="store_true", help="不传关键词，直接拉最新岗位流")
    args = ap.parse_args()

    if not args.keyword and not args.latest:
        print("CONFIG_MISSING 需要 --keyword 或 --latest（不要拉全库，总量 400+ 无意义）", file=sys.stderr)
        sys.exit(2)

    base_params: dict = {"sort": "datePosted"}
    if args.work_type:
        base_params["workType"] = args.work_type
    if args.region:
        base_params["regionLimit"] = args.region

    rows: list[dict] = []
    total = 0
    pages = 0
    for kw in args.keyword or [None]:
        params = {**base_params}
        if kw:
            params["keyword"] = kw
        jobs, t, p = fetch_all(params, args.limit)
        rows.extend(jobs)
        total += t
        pages += p

    # 去重（多关键词 OR 时可能重叠）+ 本地 days 过滤
    seen: set[str] = set()
    cutoff = (date.today() - timedelta(days=args.days)).isoformat() if args.days else None
    out = []
    for j in rows:
        key = str(j.get("id") or j.get("contentHash"))
        if key in seen:
            continue
        seen.add(key)
        if cutoff and (j.get("datePosted") or "")[:10] < cutoff:
            continue
        out.append(j)
    out.sort(key=lambda j: j.get("datePosted") or "", reverse=True)
    out = out[: args.limit]

    cols = ["#", "date", "type", "region", "title", "company", "tags", "applyUrl"]
    lines = ["\t".join(cols)]
    for i, j in enumerate(out, 1):
        cells = [
            str(i),
            (j.get("datePosted") or "")[:10],
            j.get("workType") or "",
            j.get("regionLimit") or "",
            (j.get("title") or "")[:60],
            (j.get("company") or "")[:24],
            ",".join(filter(None, (j.get("category") or []) + (j.get("tags") or [])))[:30],
            (j.get("applyUrl") or j.get("originalUrl") or "")[:90],
        ]
        lines.append("\t".join(cells))
    print("\n".join(lines))
    print(f"RESULT matched={len(out)} total={total} pages={pages} stopped=none")


if __name__ == "__main__":
    main()
