#!/usr/bin/env python3
"""岗位详情抓取：只读页面，不点任何按钮。单次浏览器会话可顺序抓多岗。

详情页数据走 SSR，直接在 DOM innerText 里（见 references/boss-zhipin.md「详情页与聊天」）。
什么时候用：初筛后、用户勾选前，对拟推荐 top N 与可能被点名的边界岗一批抓详情
（硬条件、招聘截止、HR 活跃都只在详情页）。不要对全部候选逐个开，也不要一岗一进程。

用法:
    python detail.py --link https://www.zhipin.com/job_detail/<id>.html [--headed]
    python detail.py --links <id或url>,<id或url>          # 单会话顺序抓
    python detail.py --links-file links.txt               # 一行一个；或 JSON 数组

输出: BOSS_DIR/detail-<id>.json（含 jdFlags）；stdout 每岗一行 RESULT，批量末行 BATCH
招聘截止已过期时额外输出 DEADLINE_EXPIRED 行（处置惯例见 references/matching.md）
退出码: 0 成功 / 2 未登录 / 1 风控或页面异常（验证码中止剩余岗位）
"""
import argparse
import re
import sys
import time
from pathlib import Path

from _lib import (BOSS_DIR, CONFIG_PATH, SEL, body_text, deadline_expired, first_page,
                  goto_guarded, has_login, is_captcha_strict, launch, read_json,
                  record_session, scan_jd_flags, shot, sync_pw, write_json)

# 兼职条款标签（2026-10-20：详情页有这些字段，列表接口没有）
TERM_LABELS = ("工作周期", "每周工期", "工作时间", "结算方式", "结算周期", "招聘截止")
# HR 活跃时间是 boss 名下一整行（「刚刚活跃/本周活跃/半年前活跃」等）。整行匹配，
# 不能子串搜——页面固定按钮「完善在线简历」会干扰子串匹配（2026-10-19 实测教训）
HR_ACTIVITY = re.compile(r"^(.{0,8}?)活跃$")
LINK_RE = re.compile(r"job_detail/([^./?]+)")


def extract_terms(text: str) -> dict:
    """从详情页文本提取兼职条款「标签: 值」。值截到下一个已知标签或行尾。"""
    terms: dict[str, str] = {}
    for label in TERM_LABELS:
        m = re.search(label + r"\s*[:：]?\s*([^\n]{1,24})", text)
        if not m:
            continue
        value = m.group(1)
        for other in TERM_LABELS:  # 值里混进下一个标签时截断
            value = value.split(other)[0]
        value = value.strip(" ：:·，,")
        if value:
            terms[label] = value
    return terms


def extract_hr_activity(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip().strip("·| ").strip()
        if "简历" in line:
            continue
        m = HR_ACTIVITY.match(line)
        if m:
            return line
    return None


def normalize_link(token: str) -> str:
    """表格里的岗位 id 或完整详情 URL → 详情 URL。"""
    token = token.strip()
    if token.startswith("http"):
        return token
    return f"https://www.zhipin.com/job_detail/{token}.html"


def collect_links(link: str | None, links: str | None, links_file: str | None) -> list[str]:
    """合并 --link / --links / --links-file，去重并保持顺序。"""
    raw: list[str] = []
    if link:
        raw.append(link)
    if links:
        raw.extend(part.strip() for part in links.split(",") if part.strip())
    if links_file:
        text = Path(links_file).read_text(encoding="utf-8")
        if text.lstrip().startswith("["):
            import json
            loaded = json.loads(text)
            raw.extend(str(x) for x in loaded)
        else:
            raw.extend(line.strip() for line in text.splitlines()
                       if line.strip() and not line.startswith("#"))
    out: list[str] = []
    seen: set[str] = set()
    for token in raw:
        url = normalize_link(token)
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def build_payload(link: str, text: str, jd: str) -> dict:
    """纯函数：页面文本 → detail JSON。jdFlags 在这里算，filter 读盘即可用。"""
    m = LINK_RE.search(link)
    jid = m.group(1) if m else time.strftime("%Y%m%d-%H%M%S")
    terms = extract_terms(text)
    payload = {
        "link": link,
        "id": jid,
        "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "hrActivity": extract_hr_activity(text),
        "terms": terms,
        "jdText": (jd or "").strip(),
        "rawText": text,  # 选择器没命中时的兜底：字段位置见 references/boss-zhipin.md
    }
    deadline = terms.get("招聘截止") or ""
    payload["deadlineExpired"] = deadline_expired(deadline) if deadline else None
    # 有 JD 容器就只扫 JD。rawText 含侧栏推荐岗，会把别的岗位的「每周N小时」算到本岗上
    blob = payload["jdText"] or text
    payload["jdFlags"] = scan_jd_flags(blob, terms)
    return payload


def emit_payload(payload: dict) -> Path:
    out = BOSS_DIR / f"detail-{payload['id']}.json"
    write_json(out, payload)
    missing = [k for k in TERM_LABELS if k not in payload["terms"]]
    print(f"[detail] HR活跃={payload['hrActivity'] or '未识别'} "
          f"条款={payload['terms'] or '未识别'} JD={len(payload['jdText'])}字"
          + (f"（缺标签: {'、'.join(missing)}，看 rawText）" if missing else ""))
    if payload.get("jdFlags"):
        print(f"JD_FLAGS {','.join(payload['jdFlags'])}")
    if payload["deadlineExpired"]:
        deadline = payload["terms"].get("招聘截止") or ""
        print(f"DEADLINE_EXPIRED 招聘截止 {deadline} 已过期（HR活跃={payload['hrActivity'] or '未识别'}）；"
              "截止过期且 HR 长期不活跃才淘汰，近期活跃交用户决策（matching.md）")
    print(f"RESULT {out}")
    return out


def fetch_page(page, link: str) -> tuple[dict | None, str | None]:
    """抓一页。返回 (payload, stop_reason)。stop_reason 非空时调用方应停止剩余岗位。"""
    diag = goto_guarded(page, link)
    if diag:
        return None, f"blank:{diag}"
    if is_captcha_strict(page):
        shot(page, "detail-captcha")
        return None, "captcha"
    text = body_text(page)
    jd = ""
    for sel in SEL["detail"]["jd"]:
        try:
            loc = page.locator(sel).first
            jd = loc.inner_text(timeout=1500)
            if jd.strip():
                break
        except Exception:
            continue
    return build_payload(link, text, jd), None


def main() -> int:
    parser = argparse.ArgumentParser(description="Boss直聘岗位详情抓取（可批量，单会话）")
    parser.add_argument("--link", help="单个岗位详情页链接或岗位 id")
    parser.add_argument("--links", help="逗号分隔的多个链接或岗位 id，单会话顺序抓取")
    parser.add_argument("--links-file", help="一行一个链接/id，或 JSON 数组")
    parser.add_argument("--headed", action="store_true", help="前台显示浏览器窗口（默认读 config.headed；false 时留在当前应用下面）")
    args = parser.parse_args()
    links = collect_links(args.link, args.links, args.links_file)
    if not links:
        parser.error("缺少 --link / --links / --links-file")

    cfg = read_json(CONFIG_PATH, {})
    headed = args.headed or bool(cfg.get("headed"))
    with sync_pw() as pw:
        ctx = launch(pw, visible=headed)
        try:
            record_session("detail")  # 一批多岗仍只计 1 次会话
            page = first_page(ctx)
            if not has_login(ctx):
                print("LOGIN_EXPIRED 登录态缺失，请先运行: python login.py")
                return 2
            ok = failed = 0
            stopped = None
            total = len(links)
            for i, link in enumerate(links, 1):
                if total > 1:
                    print(f"[detail] ({i}/{total}) {link}")
                try:
                    payload, stop = fetch_page(page, link)
                except Exception as e:
                    print(f"[detail] ERROR {link}: {type(e).__name__}: {e}")
                    failed += 1
                    continue
                if stop:
                    if stop == "captcha":
                        print("CAPTCHA 详情页触发安全验证，截图已存，剩余岗位未抓")
                        stopped = "captcha"
                    else:
                        print(f"RISK_BLANK {stop.split(':', 1)[-1]}")
                        stopped = "blank"
                    failed += 1
                    break
                emit_payload(payload)
                ok += 1
                if i < total:
                    time.sleep(1.5)
            if total > 1 or stopped:
                print(f"BATCH links={total} ok={ok} failed={failed} stopped={stopped or 'none'}")
            return 0 if ok and not stopped else 1
        finally:
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
