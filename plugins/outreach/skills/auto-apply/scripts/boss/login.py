#!/usr/bin/env python3
"""Boss直聘登录：检查 wt2 cookie，缺失时弹窗扫码（约 7 天有效）。

用法:
    python login.py            # 缺登录态时弹窗扫码（10 分钟超时）
    python login.py --check    # 只读 profile cookie，不启动浏览器

退出码: 0 已登录 / 2 未登录(--check) / 1 扫码超时或 cookie 库不可读 / 4 登录页被打成空白
"""
import argparse
import sys
import time

from _lib import (CookieReadError, first_page, goto_guarded, has_login, launch,
                  profile_has_login, shot, sync_pw)


def check_only() -> int:
    """不启动浏览器。cookie 库读失败时不要报成未登录。"""
    try:
        logged_in = profile_has_login()
    except CookieReadError as e:
        print(f"LOGIN_CHECK_FAILED {e}。未启动浏览器。")
        return 1
    if logged_in:
        print("LOGIN_OK 已有登录态（未启动浏览器）")
        return 0
    print("LOGIN_EXPIRED 登录态缺失，请运行 python login.py 扫码")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Boss直聘登录")
    parser.add_argument("--check", action="store_true", help="只读 profile 里的 wt2，不启动浏览器")
    args = parser.parse_args()
    if args.check:
        return check_only()

    with sync_pw() as pw:
        ctx = launch(pw, visible=True)  # 二维码要人扫，必须前台
        try:
            if has_login(ctx):
                print("LOGIN_OK 已有登录态")
                return 0
            print("未检测到登录态，请在弹出的浏览器窗口扫码登录（10 分钟超时，二维码过期自动刷新）...")
            page = first_page(ctx)
            diag = goto_guarded(page, "https://www.zhipin.com/web/user/?ka=header-login")
            if diag:
                print(f"RISK_BLANK {diag}")
                return 4
            # 默认停在短信验证码标签，切到扫码
            try:
                page.locator("text=APP扫码登录").first.click(timeout=3000)
            except Exception:
                pass  # 已在扫码标签或改版
            deadline = time.time() + 10 * 60
            while time.time() < deadline:
                # 二维码约 2-3 分钟过期，过期自动刷新
                try:
                    refresh = page.locator("text=点击刷新").first
                    if refresh.is_visible(timeout=500):
                        refresh.click()
                        time.sleep(2)
                except Exception:
                    pass
                if has_login(ctx):
                    time.sleep(3)
                    print("LOGIN_OK 扫码登录成功，登录态已持久化（约 7 天）")
                    return 0
                time.sleep(2)
            shot(page, "login-timeout")
            print("LOGIN_TIMEOUT 扫码超时")
            return 1
        finally:
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
