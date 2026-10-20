#!/usr/bin/env python3
"""岗位详情抓取：只读页面，不点任何按钮。提取完整 JD、兼职条款、HR 活跃时间。

详情页数据走 SSR，直接在 DOM innerText 里（见 references/boss-zhipin.md「详情页与聊天」）。
什么时候用：候选边界岗位（70 分附近）开详情核对「工作周期/每周工期/结算方式」再决定投不投；
top 候选写招呼语前取 JD 全文。不要对全部候选逐个开——慢，且积累风控信号。

用法:
    python detail.py --link https://www.zhipin.com/job_detail/<id>.html [--headed]

输出: BOSS_DIR/detail-<id>.json；stdout 末行 RESULT <路径>
退出码: 0 成功 / 2 未登录 / 1 风控或页面异常
"""
import argparse
import re
import sys
import time

from _lib import (BOSS_DIR, CONFIG_PATH, SEL, body_text, first_page, goto_guarded,
                  has_login, is_captcha_strict, launch, read_json, shot, sync_pw, write_json)

# 兼职条款标签（2026-10-20：详情页有这些字段，列表接口没有）
TERM_LABELS = ("工作周期", "每周工期", "工作时间", "结算方式", "结算周期", "招聘截止")
# HR 活跃时间是 boss 名下一整行（「刚刚活跃/本周活跃/半年前活跃」等）。整行匹配，
# 不能子串搜——页面固定按钮「完善在线简历」会干扰子串匹配（2026-10-19 实测教训）
HR_ACTIVITY = re.compile(r"^(.{0,8}?)活跃$")


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Boss直聘岗位详情抓取")
    parser.add_argument("--link", required=True, help="岗位详情页链接")
    parser.add_argument("--headed", action="store_true", help="前台显示浏览器窗口（默认读 config.headed）")
    args = parser.parse_args()

    cfg = read_json(CONFIG_PATH, {})
    headed = args.headed or bool(cfg.get("headed"))
    with sync_pw() as pw:
        ctx = launch(pw, visible=headed)
        try:
            page = first_page(ctx)
            if not has_login(ctx):
                print("LOGIN_EXPIRED 登录态缺失，请先运行: python login.py")
                return 2
            diag = goto_guarded(page, args.link)
            if diag:
                print(f"RISK_BLANK {diag}")
                return 1
            if is_captcha_strict(page):
                shot(page, "detail-captcha")
                print("CAPTCHA 详情页触发安全验证，截图已存")
                return 1

            text = body_text(page)
            jd = ""
            for sel in SEL["detail"]["jd"]:  # JD 容器多为 .job-sec-text；拿不到就用全文兜底
                try:
                    loc = page.locator(sel).first
                    jd = loc.inner_text(timeout=1500)
                    if jd.strip():
                        break
                except Exception:
                    continue

            m = re.search(r"job_detail/([^./?]+)", args.link)
            jid = m.group(1) if m else time.strftime("%Y%m%d-%H%M%S")
            payload = {
                "link": args.link,
                "id": jid,
                "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "hrActivity": extract_hr_activity(text),
                "terms": extract_terms(text),
                "jdText": jd.strip(),
                "rawText": text,  # 选择器没命中时的兜底：字段位置见 references/boss-zhipin.md
            }
            out = BOSS_DIR / f"detail-{jid}.json"
            write_json(out, payload)
            missing = [k for k in TERM_LABELS if k not in payload["terms"]]
            print(f"[detail] HR活跃={payload['hrActivity'] or '未识别'} "
                  f"条款={payload['terms'] or '未识别'} JD={len(payload['jdText'])}字"
                  + (f"（缺标签: {'、'.join(missing)}，看 rawText）" if missing else ""))
            print(f"RESULT {out}")
            return 0
        finally:
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
