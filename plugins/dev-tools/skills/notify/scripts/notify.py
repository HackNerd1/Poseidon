"""Cross-platform desktop notification sender.

Usage:
    python notify.py <title> <message>
    python notify.py --title "Task Done" --message "Debugger completed."

On Windows 10/11, uses native toast notifications via PowerShell + WinRT.
On macOS, uses osascript display notification.
On Linux, uses notify-send (libnotify).
"""

import subprocess
import sys
import platform
import argparse
import base64


def _notify_windows(title: str, message: str) -> bool:
    """Send a Windows 10/11 toast notification via PowerShell + WinRT."""
    # Encode title and message to base64 to avoid escaping issues
    title_b64 = base64.b64encode(title.encode("utf-16-le")).decode("ascii")
    msg_b64 = base64.b64encode(message.encode("utf-16-le")).decode("ascii")

    ps_script = f'''[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$title = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String("{title_b64}"))
$msg = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String("{msg_b64}"))
$textNodes = $template.GetElementsByTagName("text")
[void]$textNodes.Item(0).AppendChild($template.CreateTextNode($title))
[void]$textNodes.Item(1).AppendChild($template.CreateTextNode($msg))
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Claude Code").Show($toast)
'''

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _notify_macos(title: str, message: str) -> bool:
    """Send a macOS notification via osascript."""
    script = f'display notification "{message}" with title "{title}" sound name "default"'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _notify_linux(title: str, message: str) -> bool:
    """Send a Linux notification via notify-send."""
    result = subprocess.run(
        ["notify-send", title, message],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def send_notification(title: str, message: str) -> bool:
    """Send a desktop notification. Returns True on success."""
    system = platform.system()
    if system == "Windows":
        return _notify_windows(title, message)
    elif system == "Darwin":
        return _notify_macos(title, message)
    else:
        return _notify_linux(title, message)


def main():
    parser = argparse.ArgumentParser(
        description="Send a desktop notification."
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
        print(f"[notify] Failed to send notification on {platform.system()}", file=sys.stderr)
        sys.exit(1)
    print(f"[notify] Notification sent: {title} — {message}")


if __name__ == "__main__":
    main()
