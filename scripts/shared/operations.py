"""Operation model and plan/result rendering."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.ui import STYLE, print_section


@dataclass(frozen=True)
class Operation:
    action: str
    path: Path | None
    content: dict[str, Any] | None = None
    command: list[str] | None = None
    source: Path | None = None


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def operation_platform(operation: Operation) -> str:
    if operation.command:
        return operation.command[0]
    if operation.action == "sync-cursor":
        return "cursor"
    if operation.action == "sync-user":
        return "claude" if operation.path and ".claude" in str(operation.path) else "codex"
    if operation.action == "sync-claude":
        return "claude"
    if operation.action == "sync":
        return "codex"
    if operation.path is not None:
        path_text = str(operation.path)
        if ".claude" in path_text:
            return "claude"
        if ".cursor" in path_text:
            return "cursor"
        if ".codex" in path_text or ".agents" in path_text:
            return "codex"
    return "other"


def shorten_command(root: Path, command: list[str]) -> str:
    parts: list[str] = []
    root_text = str(root)
    for part in command:
        if part == "--json":
            continue
        if part == root_text or part.startswith(root_text + os.sep):
            parts.append(STYLE.paint("<repo>", STYLE.dim))
            continue
        parts.append(part)
    return " ".join(parts)


def describe_operation(root: Path, operation: Operation) -> str:
    if operation.command:
        return shorten_command(root, operation.command)
    if operation.path is None:
        return operation.action

    path_text = display_path(root, operation.path)
    action_labels = {
        "write": "write",
        "sync": "package",
        "sync-claude": "package",
        "sync-cursor": "skill",
        "sync-user": "skill",
        "delete": "delete",
    }
    action = action_labels.get(operation.action, operation.action)
    action_text = STYLE.paint(action, STYLE.cyan)
    if operation.source is not None:
        source = display_path(root, operation.source)
        if operation.action in {"sync", "sync-claude", "sync-cursor", "delete"}:
            source = Path(source).name
        arrow = STYLE.paint("→", STYLE.dim)
        return f"{action_text} {source} {arrow} {path_text}"
    return f"{action_text} {path_text}"


def summarize_command_output(stdout: str, stderr: str) -> str | None:
    """Turn noisy platform CLI output into a short detail line, or None to hide it."""
    text = stdout.strip() or stderr.strip()
    if not text:
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        if plugin_id := data.get("pluginId"):
            version = data.get("version")
            return f"{plugin_id}" + (f" v{version}" if version else "")
        if marketplace := data.get("marketplaceName"):
            state = "already added" if data.get("alreadyAdded") else "added"
            return f"{marketplace} ({state})"
        return None

    for line in text.splitlines():
        cleaned = line.strip()
        if "✔" in cleaned:
            cleaned = cleaned.split("✔", 1)[-1].strip()
        if cleaned.lower().startswith("successfully"):
            return cleaned
    return None


def print_plan(root: Path, operations: list[Operation]) -> None:
    print_section("Plan")
    if not operations:
        print(STYLE.paint("  (no operations)", STYLE.dim))
        return

    current_platform: str | None = None
    for operation in operations:
        platform = operation_platform(operation)
        if platform != current_platform:
            current_platform = platform
            print(STYLE.paint(platform.capitalize(), STYLE.magenta, STYLE.bold))
        bullet = STYLE.paint("•", STYLE.dim)
        print(f"  {bullet} {describe_operation(root, operation)}")


def print_done(operations: list[Operation]) -> None:
    counts: dict[str, int] = {}
    for operation in operations:
        platform = operation_platform(operation)
        counts[platform] = counts.get(platform, 0) + 1
    parts = [f"{name} {count}" for name, count in counts.items()]
    summary = " · ".join(parts) if parts else "nothing to do"
    print()
    print(f"{STYLE.paint('✔ Done', STYLE.green, STYLE.bold)}  {STYLE.paint(summary, STYLE.dim)}")
