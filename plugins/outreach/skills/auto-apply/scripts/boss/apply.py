#!/usr/bin/env python3
"""Boss直聘投递执行器：按投递计划（plan JSON）逐岗位打招呼。

用法:
    python apply.py --plan plan.json               # dry-run：只验证链路，不发送
    python apply.py --plan plan.json --execute     # 真实发送
    python apply.py --plan plan.json --limit 5     # 本次最多投 5 个

plan JSON 结构（由 Claude 在筛选/物料阶段生成）:
    {
      "batch": "2026-10-19-golang",
      "jobs": [
        {"link": "https://www.zhipin.com/job_detail/xxx.html",
         "job": "岗位名", "company": "公司名",
         "greeting": "招呼语（必填）"}
      ]
    }
    resume 字段即使出现也会被忽略：本脚本不发送附件。

输出: <plan>.result-<时间戳>.json + stdout 摘要（末行 RESULT <result路径>）。
结果文件带时间戳后缀，重跑不覆盖历史（2026-10-20 事故：重跑覆盖导致上一批结果丢失）
退出码: 0 完成（含部分失败）/ 2 未登录 / 3 触发风控中止 / 1 参数错误或计划全部无效
安全机制: 本地+平台日上限、随机间隔、批次长休息、验证码立即停、台账防重投
"""
import argparse
import json
import sys
import time
from pathlib import Path

from _lib import (sync_pw, CONFIG_PATH, DEFAULT_CONFIG, SEL, body_text, delivered_recently,
                  delivered_today_count, dump_frame_diag, find_chat_input, find_visible,
                  first_page, goto_guarded, has_login, human_type, is_captcha_strict,
                  is_daily_limit, job_key, launch, mark_delivered, rand_delay, read_json,
                  shot, write_json)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Boss直聘投递执行器")
    parser.add_argument("--plan", required=True, help="投递计划 JSON 路径")
    parser.add_argument("--execute", action="store_true", help="真实发送（默认 dry-run）")
    parser.add_argument("--limit", type=int, default=0, help="本次最多处理 N 个岗位（0=不限）")
    parser.add_argument("--headed", action="store_true", help="前台显示浏览器窗口（默认隐藏窗口后台运行；真实发送建议前台便于观察）")
    parser.add_argument("--retry", action="store_true", help="忽略 7 天台账防重，重新处理失败批次（补发场景；已沟通岗位按聊天记录内容去重，不会重发）")
    args = parser.parse_args()
    plan_path = Path(args.plan).expanduser()
    if not plan_path.exists():
        parser.error(f"plan 文件不存在: {plan_path}")
    return args


def plan_item_error(job: dict, greeting: str | None = None) -> str | None:
    """打开页面前的计划校验。缺 link / greeting 时绝不能点「立即沟通」。"""
    if not isinstance(job, dict):
        return "计划条目不是对象，未打开页面"
    if not str(job.get("link") or "").strip():
        return "计划缺 link，未打开页面"
    text = job.get("greeting") if greeting is None else greeting
    if not str(text or "").strip():
        return "计划缺 greeting，未打开页面（点击「立即沟通」会发出平台默认招呼语）"
    return None


def greet_one(ctx, page, job: dict, greeting: str, execute: bool) -> dict:
    """对单个岗位执行打招呼。返回 {status, note}。status:
    sent / would_send / already_connected / no_button / captcha / daily_limit / error
    """
    err = plan_item_error(job, greeting)
    if err:
        return {"status": "error", "note": err}
    diag = goto_guarded(page, job["link"])
    if diag:
        return {"status": "captcha", "note": diag}
    rand_delay((2.5, 5))

    if is_captcha_strict(page):
        shot(page, "apply-captcha")
        return {"status": "captcha", "note": "详情页触发安全验证"}

    snippet = greeting[:12].replace('"', "")
    reconnect = False

    # 已沟通过：仍打开会话，按聊天记录内容去重——只补发缺失的定制招呼语，绝不重发已有内容
    btn = find_visible(page, SEL["detail"]["continue_chat"], per_timeout=600)
    if btn:
        reconnect = True
        if not execute:
            return {"status": "already_connected", "note": "已有会话（继续沟通）；dry-run 不打开聊天"}
    else:
        btn = find_visible(page, SEL["detail"]["start_chat"])
        if not btn:
            shot(page, "apply-no-button")
            return {"status": "no_button", "note": "未找到「立即沟通」按钮（下线/改版/风控）"}
        if not execute:
            return {"status": "would_send", "note": "dry-run：链路可达，未发送"}

    btn.click()
    rand_delay((1.5, 3))
    if is_captcha_strict(page):
        shot(page, "apply-captcha-after-click")
        return {"status": "captcha", "note": "点击沟通后触发安全验证"}

    frame, chat_input = find_chat_input(ctx, SEL["chat"]["input"], per_timeout=1500)
    if not chat_input:
        if is_daily_limit(page):
            return {"status": "daily_limit", "note": "今日平台沟通次数已达上限"}
        shot(page, "apply-no-input")
        diag_path = dump_frame_diag(ctx, "no_input")
        return {"status": "error",
                "note": "全量探测（标签页×iframe×候选选择器）未找到聊天输入框，请人工确认会话是否已建立；"
                        f"选择器命中明细已存 {diag_path}（排查选择器是否过时用）"}
    chat_page = getattr(frame, "page", page)

    if reconnect and snippet and snippet in body_text(chat_page):
        return {"status": "already_connected", "note": "定制招呼语已在聊天记录中，不重发"}

    human_type(chat_input, greeting)
    rand_delay((0.8, 1.6))

    # 发送：先点发送按钮；没发出去（按钮 disabled 时点击无效）再回车兜底，以聊天记录校验为准
    for how in ("button", "enter"):
        if how == "button":
            send_btn = find_visible(frame, SEL["chat"]["send"], per_timeout=800)
            if send_btn:
                send_btn.click()
            else:
                page.keyboard.press("Enter")
        else:
            chat_input.press("Enter")
        rand_delay((1.5, 3))
        if snippet and snippet in body_text(chat_page):
            break
    else:
        return {"status": "error", "note": "发送后未在聊天记录校验到招呼语，可能未发出；可 --retry 补发（内容去重，不会重复打扰）"}

    if is_daily_limit(chat_page):
        return {"status": "daily_limit", "note": "发送后检测到今日上限提示"}
    if is_captcha_strict(chat_page):
        shot(chat_page, "apply-captcha-after-send")
        return {"status": "captcha", "note": "发送后触发安全验证"}

    return {"status": "sent",
            "note": ("已有会话，补发定制招呼语" if reconnect else "新会话") + "（气泡校验通过）"}


def _emit(plan_path: Path, plan: dict, mode: str, stop_reason, summary: dict, results: list) -> str:
    # 时间戳后缀：重跑不覆盖上一批结果（2026-10-20 重跑覆盖导致历史丢失）
    result_path = f"{plan_path.with_suffix('')}.result-{time.strftime('%Y%m%d-%H%M%S')}.json"
    payload = {"batch": plan.get("batch"), "mode": mode, "stopped": stop_reason,
               "summary": summary, "finishedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "results": results}
    write_json(result_path, payload)
    print(f"[apply] 汇总 {json.dumps(summary, ensure_ascii=False)} 中止={stop_reason}")
    print(f"RESULT {result_path}")
    return result_path


def _rec(job: dict) -> dict:
    greeting = job.get("greeting", "") if isinstance(job, dict) else ""
    return {"id": job_key(job) if isinstance(job, dict) else "",
            "job": job.get("job") if isinstance(job, dict) else None,
            "company": job.get("company") if isinstance(job, dict) else None,
            "link": job.get("link") if isinstance(job, dict) else None,
            "greeting": str(greeting)[:80]}


def main() -> int:
    args = parse_args()
    plan_path = Path(args.plan).expanduser()
    plan = read_json(plan_path, {})
    jobs = plan.get("jobs") or []
    if not jobs:
        print("PLAN_EMPTY plan 中没有 jobs")
        return 1
    if args.limit > 0:
        jobs = jobs[: args.limit]

    config = {**DEFAULT_CONFIG, **read_json(CONFIG_PATH, {})}
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(f"[apply] 模式={mode} 岗位数={len(jobs)} 日上限={config['dailyLimit']}"
          f" 间隔={config['delaySec']}s 批休={config['pauseEvery']}个/{config['pauseSec']}s")
    if not args.execute:
        print("[apply] dry-run 只验证岗位可达与按钮存在，未覆盖点击后聊天链路；"
              "首次 execute 出现输入框超时 error 时，用 --retry 补发（内容去重，不会重发）")
    if any(isinstance(j, dict) and j.get("resume") for j in jobs):
        print("[apply] plan 含 resume 字段，本次不发送附件，只处理招呼语")

    results = []
    summary = {"sent": 0, "would_send": 0, "already_connected": 0,
               "no_button": 0, "error": 0, "skipped": 0}
    stop_reason = None
    pending = []
    for job in jobs:
        err = plan_item_error(job)
        if err:
            rec = _rec(job)
            rec.update(status="error", note=err)
            results.append(rec)
            summary["error"] += 1
            label = f"{rec.get('company')} · {rec.get('job')}"
            print(f"[apply] 跳过 {label}: {err}")
            continue
        pending.append(job)
    if not pending:
        _emit(plan_path, plan, mode, "invalid_plan", summary, results)
        return 1

    with sync_pw() as pw:
        ctx = launch(pw, visible=args.headed or bool(config.get("headed")))
        try:
            page = first_page(ctx)
            if not has_login(ctx):
                print("LOGIN_EXPIRED 登录态缺失，请先运行: python login.py")
                _emit(plan_path, plan, mode, "login_expired", summary, results)
                return 2

            for i, job in enumerate(pending):
                key = job_key(job)
                rec = _rec(job)

                if delivered_recently(key) and not args.retry:
                    rec.update(status="skipped", note="7 天内已投递过（台账防重）")
                    results.append(rec)
                    summary["skipped"] += 1
                    continue
                if delivered_today_count() >= config["dailyLimit"]:
                    stop_reason = "daily_limit_local"
                    rec.update(status="skipped", note="达到本地日上限，剩余岗位未处理")
                    results.append(rec)
                    break

                print(f"[apply] ({i + 1}/{len(pending)}) {job.get('company')} · {job.get('job')}")
                try:
                    outcome = greet_one(ctx, page, job, job.get("greeting", ""), args.execute)
                except Exception as e:  # 单岗失败不中断批次
                    shot(page, "apply-exception")
                    outcome = {"status": "error", "note": f"异常: {type(e).__name__}: {e}"}

                rec.update(outcome)
                results.append(rec)
                summary[outcome["status"]] = summary.get(outcome["status"], 0) + 1
                print(f"[apply]   → {outcome['status']}: {outcome['note']}")

                if outcome["status"] == "sent":
                    mark_delivered({**job, "batch": plan.get("batch"), "greeting": job.get("greeting", "")})
                if outcome["status"] in ("captcha", "daily_limit"):
                    stop_reason = outcome["status"]
                    print(f"[apply] 触发中止条件（{stop_reason}），停止本批次")
                    break

                if i < len(pending) - 1:
                    if (i + 1) % config["pauseEvery"] == 0:
                        s = rand_delay(tuple(config["pauseSec"]))
                        print(f"[apply] 批次长休息 {s:.0f}s")
                    else:
                        rand_delay(tuple(config["delaySec"]))
        finally:
            ctx.close()

    _emit(plan_path, plan, mode, stop_reason, summary, results)
    return 0 if stop_reason != "captcha" else 3


if __name__ == "__main__":
    sys.exit(main())
