"""Cross-platform desktop notification sender with click-to-focus support.

Usage:
    python notify.py <title> <message>
    python notify.py --title "Task Done" --message "Debugger completed."
    python notify.py --title "Claude Code" --message "Waiting for input" --no-wait

Click behavior:
    Windows  — NotifyIcon balloon tip; clicking brings the terminal window to foreground.
    macOS    — terminal-notifier (if installed, with -activate) or osascript fallback.
    Linux    — notify-send with --action for click-to-focus.

With --no-wait, the script fires a balloon and exits after ~9s without
listening for clicks. Use this in automated/hook contexts.
"""

import subprocess
import sys
import os
import platform
import argparse
import tempfile


# ── platform detection ──────────────────────────────────────────────

SYSTEM = platform.system()


# ═══════════════════════════════════════════════════════════════════════
# Windows — NotifyIcon balloon tip with click-to-focus
# ═══════════════════════════════════════════════════════════════════════

def _get_foreground_window_ps() -> str:
    """Return PowerShell snippet that captures the foreground window handle."""
    return """
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32 {
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
}
'@
$hwnd = [Win32]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder(256)
[Win32]::GetWindowText($hwnd, $sb, 256) | Out-Null
$title = $sb.ToString()
$pid = 0
[Win32]::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
Write-Output "$hwnd|$title|$pid"
"""


def _notify_windows(title: str, message: str, no_wait: bool = False) -> bool:
    """Send a Windows toast notification.

    When no_wait is False, spawns a listener that catches clicks and brings
    the foreground window back into focus. When True, fires the toast and
    returns immediately — suitable for automated/hook contexts."""
    if no_wait:
        title_escaped = title.replace('"', '`"').replace('$', '`$')
        msg_escaped = message.replace('"', '`"').replace('$', '`$')
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.SystemIcons]::Information
$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = $icon
$balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$balloon.BalloonTipTitle = "{title_escaped}"
$balloon.BalloonTipText = "{msg_escaped}"
$balloon.Visible = $true
$balloon.ShowBalloonTip(8000)
Start-Sleep -Seconds 9
$balloon.Dispose()
Write-Output "[notify] Balloon tip shown"
'''
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=12,
        )
        if result.returncode != 0 and result.stderr:
            print(f"[notify:windows] {result.stderr.strip()}", file=sys.stderr)
        if result.stdout:
            print(result.stdout.strip())
        return result.returncode == 0

    title_escaped = title.replace('"', "'")
    msg_escaped = message.replace('"', "'")
    ps_script = rf'''
{_get_foreground_window_ps()}

$fgHwnd = $hwnd
$fgTitle = $title

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Hidden form required for NotifyIcon event dispatching
$form = New-Object System.Windows.Forms.Form
$form.WindowState = [System.Windows.Forms.FormWindowState]::Minimized
$form.ShowInTaskbar = $false
$form.TopMost = $false

$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = [System.Drawing.SystemIcons]::Information
$balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$balloon.BalloonTipTitle = '<<<TITLE>>>'
$balloon.BalloonTipText = '<<<MESSAGE>>>'

$clicked = $false
$balloon.add_BalloonTipClicked({{
    $script:clicked = $true

    # AllowSetForegroundWindow authorises us to set foreground because we
    # just received a user input event (the click on the balloon).
    [Win32]::AllowSetForegroundWindow(-1) | Out-Null

    if ($fgHwnd -ne [IntPtr]::Zero) {{
        $foreHwnd = [Win32]::GetForegroundWindow()
        $foreThr = [Win32]::GetWindowThreadProcessId($foreHwnd, [IntPtr]::Zero)
        $curThr = [Win32]::GetCurrentThreadId()
        if ($foreThr -ne $curThr) {{
            [Win32]::AttachThreadInput($curThr, $foreThr, $true) | Out-Null
        }}

        if ([Win32]::IsIconic($fgHwnd)) {{
            [Win32]::ShowWindow($fgHwnd, 9)  # SW_RESTORE
        }}

        # HWND_TOPMOST -> HWND_NOTOPMOST trick raises z-order
        $HWND_TOPMOST = [IntPtr](-1); $HWND_NOTOPMOST = [IntPtr](-2)
        $SWP_NOSIZE = 0x0001; $SWP_NOMOVE = 0x0002
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
$balloon.Visible = $true
$balloon.ShowBalloonTip(30000)

# 30s timeout timer
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 30000
$timer.Add_Tick({{
    $timer.Stop()
    $balloon.Dispose()
    $form.Close()
}})
$timer.Start()

# Run the WinForms message loop - required for NotifyIcon events to fire
[System.Windows.Forms.Application]::Run($form)

if ($clicked) {{
    Write-Output "[notify] Balloon clicked - focused window '$fgTitle'"
}} else {{
    Write-Output "[notify] Balloon shown (no click)"
}}
'''

    # Replace placeholders with actual content
    ps_script = ps_script.replace('<<<TITLE>>>', title_escaped)
    ps_script = ps_script.replace('<<<MESSAGE>>>', msg_escaped)

    # Write to temp file to avoid -Command escaping issues
    fd, tmp_path = tempfile.mkstemp(suffix='.ps1', prefix='claude_notify_')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(ps_script)

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp_path],
            capture_output=True,
            text=True,
            timeout=35,
        )
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    if result.returncode != 0 and result.stderr:
        print(f"[notify:windows] {result.stderr.strip()}", file=sys.stderr)
    if result.stdout:
        print(result.stdout.strip())
    return result.returncode == 0
    if result.returncode != 0 and result.stderr:
        print(f"[notify:windows] {result.stderr.strip()}", file=sys.stderr)
    if result.stdout:
        print(result.stdout.strip())
    return result.returncode == 0


# ═══════════════════════════════════════════════════════════════════════
# macOS — terminal-notifier (preferred) or osascript fallback
# ═══════════════════════════════════════════════════════════════════════

def _notify_macos(title: str, message: str) -> bool:
    """Send a macOS notification. Tries terminal-notifier first (supports
    click-to-activate), falls back to osascript."""
    # terminal-notifier supports -activate to bring the calling app to foreground
    if _has_terminal_notifier():
        result = subprocess.run(
            [
                "terminal-notifier",
                "-title", title,
                "-message", message,
                "-activate", "com.googlecode.iterm2",
                "-sender", "com.googlecode.iterm2",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("[notify:macos] terminal-notifier sent (click to focus)")
            return True

    # osascript fallback — no click support
    escaped_msg = message.replace('"', '\\"')
    escaped_title = title.replace('"', '\\"')
    script = f'display notification "{escaped_msg}" with title "{escaped_title}" sound name "default"'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("[notify:macos] osascript notification sent")
    return result.returncode == 0


def _has_terminal_notifier() -> bool:
    """Check whether terminal-notifier is available on PATH."""
    result = subprocess.run(
        ["which", "terminal-notifier"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


# ═══════════════════════════════════════════════════════════════════════
# Linux — notify-send with --action for click handling
# ═══════════════════════════════════════════════════════════════════════

def _notify_linux(title: str, message: str) -> bool:
    """Send a Linux notification via notify-send.  Uses --action to add
    a 'Focus' button when the notification daemon supports it."""
    # Try with an action button first (GNOME Shell, KDE, most modern DEs)
    result = subprocess.run(
        [
            "notify-send",
            "--urgency=normal",
            "--action=focus=Focus",
            title,
            message,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Fall back to bare notify-send without actions
        result = subprocess.run(
            ["notify-send", title, message],
            capture_output=True,
            text=True,
        )
    if result.returncode == 0:
        print("[notify:linux] notify-send sent (click action: focus)")
    return result.returncode == 0


# ═══════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════

def send_notification(title: str, message: str, no_wait: bool = False) -> bool:
    """Send a desktop notification. Returns True on success."""
    if SYSTEM == "Windows":
        return _notify_windows(title, message, no_wait=no_wait)
    elif SYSTEM == "Darwin":
        return _notify_macos(title, message)
    else:
        return _notify_linux(title, message)


def main():
    parser = argparse.ArgumentParser(
        description="Send a desktop notification with click-to-focus support."
    )
    parser.add_argument("title", nargs="?", help="Notification title")
    parser.add_argument("message", nargs="?", help="Notification body")
    parser.add_argument("--title", "-t", dest="title_opt", help="Notification title")
    parser.add_argument("--message", "-m", dest="message_opt", help="Notification body")
    parser.add_argument(
        "--no-wait", "-n",
        action="store_true",
        help="Fire toast and exit immediately (no click listener). Use in hooks/automation."
    )

    args = parser.parse_args()

    title = args.title_opt or args.title or "Claude Code"
    message = args.message_opt or args.message or "Task completed."

    success = send_notification(title, message, no_wait=args.no_wait)
    if not success:
        print(
            f"[notify] Failed to send notification on {SYSTEM}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
