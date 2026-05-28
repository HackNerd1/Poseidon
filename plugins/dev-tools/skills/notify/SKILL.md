---
name: notify
description: Send desktop system notification. Triggers after other skill tasks complete to notify the user. Use cases: notify when a long-running task finishes, send a completion alert after debugger/enhance-paper/write-paper workflows end.
arguments: [<task description or completion message>]
---

# Notification Skill

## Overview

Send a desktop system notification to alert the user when a task or skill workflow completes. Uses platform-native notification mechanisms — Windows 10/11 toast, macOS Notification Center, or Linux libnotify.

## Core Responsibilities

1. Accept a task description as argument (what just completed)
2. Call the cross-platform `notify.py` script to fire a desktop notification
3. Report success or failure back to the caller

## Workflow

### Step 1: Receive Task Context

When invoked, identify the completed task context. The skill accepts one argument — a short description of the completed task, e.g.:

- `/notify Debugger — analysis complete`
- `/notify 论文优化完成`
- `/notify Log-based bug diagnosis finished, found 2 root causes`

If no argument is provided, use a generic message: `Task completed.`

### Step 2: Send Notification

Run the notification script:

```bash
python ./scripts/notify.py "Claude Code" "<task description>"
```

The script auto-detects the platform and sends the appropriate notification.

### Step 3: Confirm

Report to the user that the notification was sent. If the script fails (non-zero exit code), report the error and suggest checking that the notification system is available.

## Input

- **Argument**: A short task description (recommended: include the source skill name and a 3-5 word summary)

## Output

- Desktop notification with title "Claude Code" and the task description as body
- Console confirmation line

## Key Rules

1. Keep the message concise — toast notifications truncate at ~200 characters
2. Always use the script path relative to the skill root (`./scripts/notify.py`)
3. Do not block waiting for the notification — it fires and returns immediately

## Limitations

- Windows: Requires Windows 10+ for native toast support
- macOS: Requires Notification Center access (granted on first use)
- Linux: Requires `libnotify-bin` / `notify-send` installed
- Not suitable for critical alerts that require user acknowledgment — this is a fire-and-forget notification
