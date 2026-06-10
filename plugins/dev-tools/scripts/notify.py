"""Cross-platform desktop notification sender with click-to-focus support.

Usage:
    python notify.py <title> <message>
    python notify.py --title "Task Done" --message "Debugger completed."
    python notify.py --title "Claude Code" --message "Waiting for input"

Click behavior:
    Windows  — clicking the toast brings the terminal window back to foreground.
    macOS    — uses terminal-notifier (if installed) with -activate flag; falls back to osascript.
    Linux    — notify-send with --action supports click-to-focus.

On Windows, the script captures the current foreground window and spawns a
short-lived background listener (~30s) to handle toast activation clicks.
"""

import subprocess
import sys
import platform
import argparse
import base64
import os
import tempfile
import time


# ── platform detection ──────────────────────────────────────────────

SYSTEM = platform.system()


# ═══════════════════════════════════════════════════════════════════════
# Windows — PowerShell + WinRT toast with click-to-focus
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


def _notify_windows(title: str, message: str) -> bool:
    """Send a Windows toast notification. Spawns a listener that catches
    clicks and brings the foreground window back into focus."""
    title_b64 = base64.b64encode(title.encode("utf-16-le")).decode("ascii")
    msg_b64 = base64.b64encode(message.encode("utf-16-le")).decode("ascii")

    ps_script = rf'''
{_get_foreground_window_ps()}

$fgInfo = "$hwnd|$title|$pid"
$fgHwnd = $hwnd
$fgTitle = $title

# Store window info so external helpers can read it
$infoFile = Join-Path $env:TEMP "claude_code_focus.txt"
$fgInfo | Out-File -FilePath $infoFile -Encoding utf8

# Build toast XML
$titleB64 = "{title_b64}"
$msgB64 = "{msg_b64}"
$titleDecoded = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String($titleB64))
$msgDecoded = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String($msgB64))

$xml = @"
<toast scenario="reminder" activationType="foreground">
  <visual>
    <binding template="ToastText02">
      <text id="1">$titleDecoded</text>
      <text id="2">$msgDecoded</text>
    </binding>
  </visual>
  <actions>
    <action content="Focus Claude Code" arguments="focus" activationType="foreground"/>
  </actions>
</toast>
"@

$xmlDoc = New-Object Windows.Data.Xml.Dom.XmlDocument
$xmlDoc.LoadXml($xml)

$toast = [Windows.UI.Notifications.ToastNotification]::new($xmlDoc)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Claude Code")

# Register for the Activated event (fires when user clicks the toast or action button)
$eventId = "ToastActivated_" + (Get-Random)
Register-ObjectEvent -InputObject $toast -EventName Activated -SourceIdentifier $eventId | Out-Null
Register-ObjectEvent -InputObject $toast -EventName Dismissed -SourceIdentifier ($eventId + "_Dismissed") | Out-Null

$notifier.Show($toast)

# Wait up to 30s for a click, then clean up
$timeout = 30
$clicked = $false
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt $timeout) {{
    $evt = Wait-Event -Timeout 1000
    if ($evt) {{
        if ($evt.SourceIdentifier -eq $eventId) {{
            $clicked = $true
            # Bring the original window back to foreground
            try {{
                if ($fgHwnd -ne [IntPtr]::Zero) {{
                    if ([Win32]::IsIconic($fgHwnd)) {{
                        [Win32]::ShowWindow($fgHwnd, 9)  # SW_RESTORE
                    }}
                    [Win32]::SetForegroundWindow($fgHwnd)
                }}
            }} catch {{ }}
            Remove-Event -EventIdentifier $evt.EventIdentifier
            break
        }}
        if ($evt.SourceIdentifier -eq ($eventId + "_Dismissed")) {{
            Remove-Event -EventIdentifier $evt.EventIdentifier
            break
        }}
        Remove-Event -EventIdentifier $evt.EventIdentifier
    }}
}}
$sw.Stop()

# Cleanup
Unregister-Event -SourceIdentifier $eventId -ErrorAction SilentlyContinue
Unregister-Event -SourceIdentifier ($eventId + "_Dismissed") -ErrorAction SilentlyContinue
Remove-Item $infoFile -ErrorAction SilentlyContinue

if ($clicked) {{
    Write-Output "[notify] Toast clicked — focused window '$fgTitle'"
}} else {{
    Write-Output "[notify] Toast shown (no click)"
}}
'''

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        timeout=35,  # slightly longer than the 30s internal wait
    )
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

def send_notification(title: str, message: str) -> bool:
    """Send a desktop notification. Returns True on success."""
    if SYSTEM == "Windows":
        return _notify_windows(title, message)
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

    args = parser.parse_args()

    title = args.title_opt or args.title or "Claude Code"
    message = args.message_opt or args.message or "Task completed."

    success = send_notification(title, message)
    if not success:
        print(
            f"[notify] Failed to send notification on {SYSTEM}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
