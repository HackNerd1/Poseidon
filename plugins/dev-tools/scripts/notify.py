"""Cross-platform desktop notification sender with click-to-focus support.

Usage:
    python notify.py <title> <message>
    python notify.py --title "Task Done" --message "Debugger completed."
    python notify.py --title "Codex" --message "Response ready" --no-wait --quiet --best-effort

Click behavior:
    Windows  - NotifyIcon balloon; click restores the foreground window captured at notification time.
    macOS    - terminal-notifier activates the foreground app captured at notification time.
               osascript fallback can show a notification, but cannot reliably focus on click.
    Linux    - notify-send action plus xdotool/wmctrl focuses the captured X11 window when supported.

Use --no-wait in hooks. On Windows/Linux it starts a short-lived detached listener
when click handling needs one, then returns immediately.
"""

from __future__ import annotations

import argparse
import base64
import os
import platform
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass


SYSTEM = platform.system()
QUIET = False


@dataclass(frozen=True)
class MacTarget:
    bundle_id: str
    app_name: str


@dataclass(frozen=True)
class LinuxTarget:
    window_id: str


def _info(message: str) -> None:
    if not QUIET:
        print(message)


def _run(command: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _popen_detached(command: list[str]) -> bool:
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if SYSTEM == "Windows":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen(command, **kwargs)
        return True
    except OSError:
        return False


def _shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


# Windows -----------------------------------------------------------------

def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _ps_encoded_command(script: str) -> str:
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def _windows_notify_script(title: str, message: str, timeout_seconds: int) -> str:
    title_literal = _ps_single_quote(title)
    message_literal = _ps_single_quote(message)
    return f"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool AllowSetForegroundWindow(int dwProcessId);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
}}
'@

$fgHwnd = [Win32]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder(256)
[Win32]::GetWindowText($fgHwnd, $sb, 256) | Out-Null
$fgTitle = $sb.ToString()

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.WindowState = [System.Windows.Forms.FormWindowState]::Minimized
$form.ShowInTaskbar = $false
$form.TopMost = $false

$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = [System.Drawing.SystemIcons]::Information
$balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$balloon.BalloonTipTitle = {title_literal}
$balloon.BalloonTipText = {message_literal}

$balloon.add_BalloonTipClicked({{
    [Win32]::AllowSetForegroundWindow(-1) | Out-Null
    if ($fgHwnd -ne [IntPtr]::Zero) {{
        $foreHwnd = [Win32]::GetForegroundWindow()
        $foreThr = [Win32]::GetWindowThreadProcessId($foreHwnd, [IntPtr]::Zero)
        $curThr = [Win32]::GetCurrentThreadId()
        if ($foreThr -ne $curThr) {{
            [Win32]::AttachThreadInput($curThr, $foreThr, $true) | Out-Null
        }}
        if ([Win32]::IsIconic($fgHwnd)) {{
            [Win32]::ShowWindow($fgHwnd, 9) | Out-Null
        }}
        $HWND_TOPMOST = [IntPtr](-1)
        $HWND_NOTOPMOST = [IntPtr](-2)
        $SWP_NOSIZE = 0x0001
        $SWP_NOMOVE = 0x0002
        [Win32]::SetWindowPos($fgHwnd, $HWND_TOPMOST, 0, 0, 0, 0, $SWP_NOSIZE -bor $SWP_NOMOVE) | Out-Null
        [Win32]::SetWindowPos($fgHwnd, $HWND_NOTOPMOST, 0, 0, 0, 0, $SWP_NOSIZE -bor $SWP_NOMOVE) | Out-Null
        [Win32]::SetForegroundWindow($fgHwnd) | Out-Null
        if ($foreThr -ne $curThr) {{
            [Win32]::AttachThreadInput($curThr, $foreThr, $false) | Out-Null
        }}
    }}
    $balloon.Dispose()
    $form.Close()
}})

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = {timeout_seconds * 1000}
$timer.Add_Tick({{
    $timer.Stop()
    $balloon.Dispose()
    $form.Close()
}})
$timer.Start()

$balloon.Visible = $true
$balloon.ShowBalloonTip({timeout_seconds * 1000})
[System.Windows.Forms.Application]::Run($form)
"""


def _notify_windows(title: str, message: str, no_wait: bool, timeout_seconds: int) -> bool:
    encoded = _ps_encoded_command(_windows_notify_script(title, message, timeout_seconds))
    command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]
    if no_wait:
        return _popen_detached(command)

    result = _run(command, timeout=timeout_seconds + 5)
    if result.returncode == 0:
        _info("[notify:windows] notification sent")
    return result.returncode == 0


# macOS -------------------------------------------------------------------

def _mac_frontmost_target() -> MacTarget | None:
    script = """
tell application "System Events"
    set frontApp to first application process whose frontmost is true
    set appName to name of frontApp
    try
        set bundleId to bundle identifier of frontApp
    on error
        set bundleId to ""
    end try
end tell
return bundleId & "\t" & appName
"""
    try:
        result = _run(["osascript", "-e", script], timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        result = None

    if result and result.returncode == 0:
        raw = result.stdout.strip()
        if raw:
            bundle_id, _, app_name = raw.partition("\t")
            if bundle_id:
                return MacTarget(bundle_id=bundle_id, app_name=app_name or bundle_id)

    term_program = os.environ.get("TERM_PROGRAM", "")
    fallback_ids = {
        "Apple_Terminal": ("com.apple.Terminal", "Terminal"),
        "iTerm.app": ("com.googlecode.iterm2", "iTerm2"),
        "WezTerm": ("com.github.wez.wezterm", "WezTerm"),
        "vscode": ("com.microsoft.VSCode", "Visual Studio Code"),
    }
    if term_program in fallback_ids:
        bundle_id, app_name = fallback_ids[term_program]
        return MacTarget(bundle_id=bundle_id, app_name=app_name)
    return None


def _notify_macos(title: str, message: str) -> bool:
    target = _mac_frontmost_target()

    if shutil.which("terminal-notifier"):
        command = ["terminal-notifier", "-title", title, "-message", message]
        if target:
            command.extend(["-activate", target.bundle_id])
        result = _run(command, timeout=10)
        if result.returncode != 0 and target:
            result = _run(["terminal-notifier", "-title", title, "-message", message], timeout=10)
        if result.returncode == 0:
            suffix = f" (click activates {target.app_name})" if target else ""
            _info(f"[notify:macos] terminal-notifier sent{suffix}")
            return True

    escaped_msg = message.replace("\\", "\\\\").replace('"', '\\"')
    escaped_title = title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display notification "{escaped_msg}" with title "{escaped_title}" sound name "default"'
    result = _run(["osascript", "-e", script], timeout=5)
    if result.returncode == 0:
        _info("[notify:macos] osascript notification sent (click-to-focus unavailable)")
    return result.returncode == 0


# Linux -------------------------------------------------------------------

def _linux_frontmost_target() -> LinuxTarget | None:
    if not os.environ.get("DISPLAY"):
        return None
    if shutil.which("xdotool"):
        result = _run(["xdotool", "getactivewindow"], timeout=3)
        window_id = result.stdout.strip()
        if result.returncode == 0 and window_id:
            return LinuxTarget(window_id=window_id)
    return None


def _focus_linux_window(target: LinuxTarget) -> None:
    if shutil.which("xdotool"):
        subprocess.run(
            ["xdotool", "windowactivate", "--sync", target.window_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return
    if shutil.which("wmctrl"):
        subprocess.run(
            ["wmctrl", "-ia", target.window_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )


def _notify_linux_worker(title: str, message: str, target: LinuxTarget | None, timeout_seconds: int) -> bool:
    if not shutil.which("notify-send"):
        return False

    if target and (shutil.which("xdotool") or shutil.which("wmctrl")):
        try:
            result = _run(
                [
                    "notify-send",
                    "--urgency=normal",
                    "--action=focus=Focus",
                    "--expire-time",
                    str(timeout_seconds * 1000),
                    title,
                    message,
                ],
                timeout=timeout_seconds + 5,
            )
        except subprocess.TimeoutExpired:
            return True

        if result.returncode == 0 and result.stdout.strip() == "focus":
            _focus_linux_window(target)
        return result.returncode == 0

    result = _run(["notify-send", "--urgency=normal", title, message], timeout=5)
    return result.returncode == 0


def _notify_linux(title: str, message: str, no_wait: bool, timeout_seconds: int) -> bool:
    target = _linux_frontmost_target()
    if no_wait and target:
        command = [
            sys.executable,
            os.path.abspath(__file__),
            "--linux-worker",
            "--title",
            title,
            "--message",
            message,
            "--focus-window",
            target.window_id,
            "--timeout",
            str(timeout_seconds),
        ]
        if QUIET:
            command.append("--quiet")
        return _popen_detached(command)

    ok = _notify_linux_worker(title, message, target, timeout_seconds)
    if ok:
        suffix = " (click action enabled)" if target else ""
        _info(f"[notify:linux] notify-send sent{suffix}")
    return ok


# Public API ---------------------------------------------------------------

def send_notification(title: str, message: str, no_wait: bool = False, timeout_seconds: int = 30) -> bool:
    if SYSTEM == "Windows":
        return _notify_windows(title, message, no_wait=no_wait, timeout_seconds=timeout_seconds)
    if SYSTEM == "Darwin":
        return _notify_macos(title, message)
    return _notify_linux(title, message, no_wait=no_wait, timeout_seconds=timeout_seconds)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a desktop notification with best-effort click-to-focus support."
    )
    parser.add_argument("title", nargs="?", help="Notification title")
    parser.add_argument("message", nargs="?", help="Notification body")
    parser.add_argument("--title", "-t", dest="title_opt", help="Notification title")
    parser.add_argument("--message", "-m", dest="message_opt", help="Notification body")
    parser.add_argument(
        "--no-wait",
        "-n",
        action="store_true",
        help="Return immediately; spawn a short-lived click listener when the platform requires one.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Seconds to keep click listeners alive on platforms that need one.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational stdout. Use for Codex hooks that reserve stdout for JSON.",
    )
    parser.add_argument(
        "--best-effort",
        action="store_true",
        help="Return success even if the desktop notification backend is unavailable.",
    )
    parser.add_argument("--linux-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--focus-window", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global QUIET

    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    QUIET = args.quiet

    title = args.title_opt or args.title or "Poseidon"
    message = args.message_opt or args.message or "Task completed."
    timeout_seconds = max(1, args.timeout)

    if args.linux_worker:
        target = LinuxTarget(args.focus_window) if args.focus_window else None
        success = _notify_linux_worker(title, message, target, timeout_seconds)
    else:
        success = send_notification(title, message, no_wait=args.no_wait, timeout_seconds=timeout_seconds)

    if not success and not args.best_effort:
        print(f"[notify] Failed to send notification on {SYSTEM}", file=sys.stderr)
        return 1
    if success and not args.linux_worker:
        _info(f"[notify] sent via {SYSTEM}; command={_shell_join(sys.argv)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
