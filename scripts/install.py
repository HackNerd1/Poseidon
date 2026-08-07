#!/usr/bin/env python3
"""Poseidon platform matrix installer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adapters import claude, codex, cursor
from platform_matrix import implemented_platforms


SCOPES = ("repo", "user")
SUPPORTED_SCOPES = {
    "codex": ("repo",),
    "claude": ("repo",),
    "cursor": ("repo", "user"),
}

# Modifier flags that may accompany interactive mode without selecting a target.
_INTERACTIVE_OK_FLAGS = frozenset(
    {
        "--interactive",
        "--dry-run",
        "--generate-only",
        "--yes",
        "--scope",
        "--plugin",
    }
)


@dataclass(frozen=True)
class Operation:
    action: str
    path: Path | None
    content: dict[str, Any] | None = None
    command: list[str] | None = None
    source: Path | None = None


class _Style:
    """ANSI helpers; degrade cleanly when stdout is not a TTY."""

    def __init__(self) -> None:
        enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        self.enabled = enabled
        self.reset = "\033[0m" if enabled else ""
        self.bold = "\033[1m" if enabled else ""
        self.dim = "\033[2m" if enabled else ""
        self.cyan = "\033[36m" if enabled else ""
        self.green = "\033[32m" if enabled else ""
        self.yellow = "\033[33m" if enabled else ""
        self.red = "\033[31m" if enabled else ""
        self.magenta = "\033[35m" if enabled else ""

    def paint(self, text: str, *codes: str) -> str:
        if not self.enabled or not codes:
            return text
        return f"{''.join(codes)}{text}{self.reset}"


STYLE = _Style()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def parse_args(argv: list[str], supported_platforms: tuple[str, ...]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Poseidon plugins for agent platforms.")
    parser.add_argument("--interactive", action="store_true", help="Run the interactive CLI.")
    parser.add_argument(
        "--platform",
        default=None,
        help=(
            "Target platform, comma-separated list "
            f"({', '.join(supported_platforms)}), or use --all."
        ),
    )
    parser.add_argument("--all", action="store_true", help="Target all supported platforms.")
    parser.add_argument(
        "--scope",
        choices=SCOPES,
        default=None,
        help=(
            "Install scope. Codex/Claude support repo only; "
            "Cursor supports repo (.cursor/skills) and user (~/.cursor/skills). "
            "Default: repo."
        ),
    )
    parser.add_argument(
        "--plugin",
        default=None,
        help="Plugin name, comma-separated list, or 'all'. Default: all.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing files.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Accepted for compatibility; confirmation is no longer prompted.",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help=(
            "Only write local package/manifest files; do not register, install, or enable "
            "plugins via platform CLIs. Cursor still copies skills (copy is the install)."
        ),
    )
    return parser.parse_args(argv)


def _wants_interactive(argv: list[str], args: argparse.Namespace) -> bool:
    if args.interactive or not argv:
        return True
    if args.platform or args.all:
        return False
    # Allow `install.py --dry-run` / `--generate-only` to open the picker
    # while still honoring those flags.
    tokens = [token for token in argv if token.startswith("-")]
    for token in tokens:
        name = token.split("=", 1)[0]
        if name not in _INTERACTIVE_OK_FLAGS and name not in {"-h", "--help"}:
            return False
    return True


def _read_key() -> str:
    """Read a single keypress; returns 'up'/'down'/'enter'/'esc' or a character."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        first = sys.stdin.read(1)
        if first == "\x1b":
            rest = sys.stdin.read(2)
            if rest == "[A":
                return "up"
            if rest == "[B":
                return "down"
            return "esc"
        if first in {"\r", "\n"}:
            return "enter"
        if first in {"\x03"}:  # Ctrl-C
            raise KeyboardInterrupt
        return first
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _select_arrow(label: str, choices: list[tuple[str, str]], default: str) -> str:
    index = next((i for i, (value, _) in enumerate(choices) if value == default), 0)
    hint = STYLE.paint("↑/↓ move · enter confirm · q quit", STYLE.dim)

    def render(*, first: bool) -> None:
        if not first:
            # Move cursor up over previous menu frame.
            sys.stdout.write(f"\033[{len(choices) + 2}A")
        sys.stdout.write(f"{STYLE.paint('?', STYLE.cyan, STYLE.bold)} {STYLE.paint(label, STYLE.bold)}\n")
        for i, (_value, title) in enumerate(choices):
            if i == index:
                marker = STYLE.paint("❯", STYLE.cyan, STYLE.bold)
                text = STYLE.paint(title, STYLE.cyan, STYLE.bold)
            else:
                marker = " "
                text = title
            sys.stdout.write(f"  {marker} {text}\n")
        sys.stdout.write(f"  {hint}\n")
        sys.stdout.flush()

    render(first=True)
    while True:
        key = _read_key()
        if key == "up":
            index = (index - 1) % len(choices)
            render(first=False)
        elif key == "down":
            index = (index + 1) % len(choices)
            render(first=False)
        elif key == "enter":
            selected = choices[index]
            _finish_select_summary(label, selected[1], len(choices) + 1)
            return selected[0]
        elif key in {"q", "esc"}:
            raise SystemExit(STYLE.paint("Aborted.", STYLE.dim))


def _select_numbered(label: str, choices: list[tuple[str, str]], default: str) -> str:
    print(f"\n{STYLE.paint('?', STYLE.cyan, STYLE.bold)} {STYLE.paint(label, STYLE.bold)}")
    for i, (value, title) in enumerate(choices, start=1):
        suffix = STYLE.paint(" (default)", STYLE.dim) if value == default else ""
        print(f"  {STYLE.paint(str(i), STYLE.dim)}. {title}{suffix}")
    raw = input(f"{STYLE.paint('❯', STYLE.cyan)} ").strip()
    if not raw:
        return default
    if raw.isdigit() and 1 <= int(raw) <= len(choices):
        return choices[int(raw) - 1][0]
    values = {value for value, _title in choices}
    if raw in values:
        return raw
    raise SystemExit(f"Invalid choice: {raw}")


def select_choice(label: str, choices: list[tuple[str, str]], default: str) -> str:
    if not choices:
        raise SystemExit("No choices available.")
    values = {value for value, _title in choices}
    if default not in values:
        default = choices[0][0]
    use_arrow = sys.stdin.isatty() and sys.stdout.isatty() and sys.platform != "win32"
    if use_arrow:
        try:
            return _select_arrow(label, choices, default)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except (ImportError, OSError):
            pass
    return _select_numbered(label, choices, default)


def _finish_select_summary(label: str, summary_value: str, lines: int) -> None:
    sys.stdout.write("\033[1A\033[2K")
    summary = (
        f"{STYLE.paint('✔', STYLE.green)} {STYLE.paint(label, STYLE.bold)} "
        f"{STYLE.paint(summary_value, STYLE.cyan)}"
    )
    sys.stdout.write(f"\033[{lines}A")
    sys.stdout.write("\033[J")
    sys.stdout.write(summary + "\n")
    sys.stdout.flush()


def _select_multi_arrow(
    label: str,
    choices: list[tuple[str, str]],
    defaults: set[str],
) -> list[str]:
    index = 0
    selected = {value for value, _title in choices if value in defaults}
    hint = STYLE.paint("↑/↓ move · space toggle · a all · enter confirm · q quit", STYLE.dim)

    def render(*, first: bool) -> None:
        if not first:
            sys.stdout.write(f"\033[{len(choices) + 2}A")
        sys.stdout.write(f"{STYLE.paint('?', STYLE.cyan, STYLE.bold)} {STYLE.paint(label, STYLE.bold)}\n")
        for i, (value, title) in enumerate(choices):
            checked = value in selected
            box = STYLE.paint("◉", STYLE.cyan) if checked else STYLE.paint("◯", STYLE.dim)
            if i == index:
                marker = STYLE.paint("❯", STYLE.cyan, STYLE.bold)
                text = STYLE.paint(title, STYLE.cyan, STYLE.bold)
            else:
                marker = " "
                text = title
            sys.stdout.write(f"  {marker} {box} {text}\n")
        sys.stdout.write(f"  {hint}\n")
        sys.stdout.flush()

    render(first=True)
    while True:
        key = _read_key()
        if key == "up":
            index = (index - 1) % len(choices)
            render(first=False)
        elif key == "down":
            index = (index + 1) % len(choices)
            render(first=False)
        elif key == " ":
            value = choices[index][0]
            if value in selected:
                selected.remove(value)
            else:
                selected.add(value)
            render(first=False)
        elif key == "a":
            values = {value for value, _title in choices}
            selected = set() if selected == values else values
            render(first=False)
        elif key == "enter":
            if not selected:
                continue
            ordered = [value for value, _title in choices if value in selected]
            titles = [title for value, title in choices if value in selected]
            summary = "All" if len(ordered) == len(choices) else ", ".join(titles)
            _finish_select_summary(label, summary, len(choices) + 1)
            return ordered
        elif key in {"q", "esc"}:
            raise SystemExit(STYLE.paint("Aborted.", STYLE.dim))


def _select_multi_numbered(
    label: str,
    choices: list[tuple[str, str]],
    defaults: set[str],
) -> list[str]:
    default_values = [value for value, _title in choices if value in defaults]
    print(f"\n{STYLE.paint('?', STYLE.cyan, STYLE.bold)} {STYLE.paint(label, STYLE.bold)}")
    print(STYLE.paint("  comma-separated numbers or 'all' (required)", STYLE.dim))
    for i, (value, title) in enumerate(choices, start=1):
        mark = STYLE.paint("*", STYLE.cyan) if value in default_values else " "
        print(f"  {STYLE.paint(str(i), STYLE.dim)}. [{mark}] {title}")
    raw = input(f"{STYLE.paint('❯', STYLE.cyan)} ").strip().lower()
    if not raw:
        if default_values:
            return default_values
        raise SystemExit("Select at least one option.")
    if raw == "all":
        return [value for value, _title in choices]
    picked: list[str] = []
    for token in raw.replace(" ", "").split(","):
        if not token:
            continue
        if token.isdigit() and 1 <= int(token) <= len(choices):
            value = choices[int(token) - 1][0]
            if value not in picked:
                picked.append(value)
            continue
        values = {value for value, _title in choices}
        if token in values and token not in picked:
            picked.append(token)
            continue
        raise SystemExit(f"Invalid choice: {token}")
    if not picked:
        raise SystemExit("Select at least one option.")
    return picked


def select_multiple(
    label: str,
    choices: list[tuple[str, str]],
    defaults: set[str] | None = None,
) -> list[str]:
    if not choices:
        raise SystemExit("No choices available.")
    default_set = set(defaults) if defaults is not None else set()
    use_arrow = sys.stdin.isatty() and sys.stdout.isatty() and sys.platform != "win32"
    if use_arrow:
        try:
            return _select_multi_arrow(label, choices, default_set)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except (ImportError, OSError):
            pass
    return _select_multi_numbered(label, choices, default_set)


def encode_plugin_arg(selected: list[str], all_names: list[str]) -> str:
    if not selected or set(selected) == set(all_names):
        return "all"
    return ",".join(selected)


def encode_platform_arg(selected: list[str], supported: tuple[str, ...] | list[str]) -> tuple[bool, str | None]:
    """Return (all_flag, platform_arg) for selected platforms."""
    if not selected or set(selected) == set(supported):
        return True, None
    return False, ",".join(selected)


def print_banner() -> None:
    title = STYLE.paint("Poseidon Installer", STYLE.bold, STYLE.magenta)
    subtitle = STYLE.paint("platform matrix · interactive setup", STYLE.dim)
    print(f"\n{title}")
    print(subtitle)
    print(STYLE.paint("─" * 36, STYLE.dim))


def interactive_fill(root: Path, supported_platforms: tuple[str, ...], args: argparse.Namespace) -> argparse.Namespace:
    """Prompt for missing install choices; CLI modifiers (--dry-run etc.) are preserved."""
    print_banner()

    if args.platform or args.all:
        selected_platforms = (
            list(supported_platforms)
            if args.all
            else [part.strip() for part in args.platform.split(",") if part.strip()]
        )
    else:
        platform_choices = [(platform, platform.capitalize()) for platform in supported_platforms]
        selected_platforms = select_multiple("Select target platforms", platform_choices)

    if args.plugin is not None:
        plugin = args.plugin
    else:
        plugin_dirs = codex.discover_plugin_dirs(root)
        plugin_names = [path.name for path in plugin_dirs]
        plugin_choices = [(name, name) for name in plugin_names]
        selected_plugins = select_multiple("Select plugins", plugin_choices)
        plugin = encode_plugin_arg(selected_plugins, plugin_names)

    if args.scope is not None:
        scope = args.scope
    else:
        scope = "repo"
        # When installing multiple platforms, keep Codex/Claude on repo and only
        # offer Cursor scope when Cursor is the sole target.
        if selected_platforms == ["cursor"]:
            scope_choices = [
                ("repo", "Repo (.cursor/skills)"),
                ("user", "User (~/.cursor/skills)"),
            ]
            scope = select_choice("Select Cursor install scope", scope_choices, "repo")

    args.interactive = True
    args.all, args.platform = encode_platform_arg(selected_platforms, supported_platforms)
    args.scope = scope
    args.plugin = plugin
    return args


def target_platforms(args: argparse.Namespace) -> list[str]:
    supported = list(args.supported_platforms)
    if args.all:
        return supported
    if not args.platform:
        raise SystemExit("Specify --platform, --all, or run with no arguments for interactive mode.")

    names = [part.strip() for part in args.platform.split(",") if part.strip()]
    if not names or "all" in names:
        return supported

    unknown = [name for name in names if name not in supported]
    if unknown:
        known = ", ".join(supported) or "(none)"
        raise SystemExit(f"Unknown platform(s): {', '.join(unknown)}. Known platforms: {known}")

    # Keep matrix order stable regardless of CLI/input order.
    selected = set(names)
    return [name for name in supported if name in selected]


def validate_scope(platform: str, scope: str) -> None:
    if scope not in SUPPORTED_SCOPES.get(platform, SCOPES):
        supported = ", ".join(SUPPORTED_SCOPES.get(platform, SCOPES))
        raise ValueError(
            f"{platform.capitalize()} does not support --scope {scope}; "
            f"supported scope: {supported}."
        )


def codex_plan(root: Path, scope: str, plugin: str, generate_only: bool) -> list[Operation]:
    validate_scope("codex", scope)

    selected_plugin_dirs = codex.select_plugin_dirs(root, plugin)
    all_plugin_dirs = codex.discover_plugin_dirs(root)
    operations: list[Operation] = []
    operations.append(
        Operation(
            "write",
            codex.marketplace_path(root),
            codex.generate_marketplace(root, all_plugin_dirs),
        )
    )
    for plugin_dir in all_plugin_dirs:
        operations.append(
            Operation(
                "sync",
                codex.package_plugin_path(root, plugin_dir.name),
                source=plugin_dir,
            )
        )
    if not generate_only:
        operations.append(
            Operation(
                "run",
                None,
                command=["codex", "plugin", "marketplace", "add", str(root), "--json"],
            )
        )
        for plugin_dir in selected_plugin_dirs:
            operations.append(
                Operation(
                    "run",
                    None,
                    command=[
                        "codex",
                        "plugin",
                        "add",
                        f"{plugin_dir.name}@{codex.marketplace_name(root)}",
                        "--json",
                    ],
                )
            )
    return operations


def claude_plan(root: Path, scope: str, plugin: str, generate_only: bool) -> list[Operation]:
    validate_scope("claude", scope)

    selected_plugin_dirs = codex.select_plugin_dirs(root, plugin)
    all_plugin_dirs = claude.discover_plugin_dirs(root)
    operations: list[Operation] = [
        Operation(
            "write",
            claude.marketplace_path(root),
            claude.generate_marketplace(root, all_plugin_dirs),
        )
    ]
    for plugin_dir in all_plugin_dirs:
        operations.append(
            Operation(
                "sync-claude",
                claude.package_plugin_path(root, plugin_dir.name),
                source=plugin_dir,
            )
        )
    if not generate_only:
        operations.append(
            Operation(
                "run",
                None,
                command=["claude", "plugin", "marketplace", "add", str(root)],
            )
        )
        for plugin_dir in selected_plugin_dirs:
            operations.append(
                Operation(
                    "run",
                    None,
                    command=[
                        "claude",
                        "plugin",
                        "install",
                        f"{plugin_dir.name}@{codex.marketplace_name(root)}",
                        "--scope",
                        "project" if scope == "repo" else scope,
                    ],
                )
            )
    return operations


def cursor_plan(root: Path, scope: str, plugin: str, generate_only: bool) -> list[Operation]:
    del generate_only  # Cursor has no separate CLI enable step; copy is the install.
    validate_scope("cursor", scope)

    plugin_dirs = cursor.select_plugin_dirs(root, plugin)
    operations: list[Operation] = []
    for skill_dir in cursor.discover_skill_dirs(plugin_dirs):
        operations.append(
            Operation(
                "sync-cursor",
                cursor.skill_target_path(root, scope, skill_dir),
                source=skill_dir,
            )
        )
    return operations


def effective_scope(platform: str, scope: str, *, multi_platform: bool) -> str:
    supported = SUPPORTED_SCOPES.get(platform, SCOPES)
    if scope in supported:
        return scope
    if multi_platform and "repo" in supported:
        # --all with Cursor user scope still installs Codex/Claude at repo scope.
        return "repo"
    validate_scope(platform, scope)
    return scope


def build_plan(
    root: Path,
    platforms: list[str],
    scope: str,
    plugin: str,
    generate_only: bool,
) -> list[Operation]:
    operations: list[Operation] = []
    multi_platform = len(platforms) > 1
    for platform in platforms:
        platform_scope = effective_scope(platform, scope, multi_platform=multi_platform)
        if platform == "codex":
            operations.extend(codex_plan(root, platform_scope, plugin, generate_only))
        elif platform == "claude":
            operations.extend(claude_plan(root, platform_scope, plugin, generate_only))
        elif platform == "cursor":
            operations.extend(cursor_plan(root, platform_scope, plugin, generate_only))
    return operations


def operation_platform(operation: Operation) -> str:
    if operation.command:
        return operation.command[0]
    if operation.action == "sync-cursor":
        return "cursor"
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
    }
    action = action_labels.get(operation.action, operation.action)
    action_text = STYLE.paint(action, STYLE.cyan)
    if operation.source is not None:
        source = display_path(root, operation.source)
        # Prefer the leaf name for package/skill sync lines.
        if operation.action in {"sync", "sync-claude", "sync-cursor"}:
            source = Path(source).name
        arrow = STYLE.paint("→", STYLE.dim)
        return f"{action_text} {source} {arrow} {path_text}"
    return f"{action_text} {path_text}"


def summarize_command_output(stdout: str, stderr: str) -> str | None:
    """Turn noisy platform CLI output into a short detail line, or None to hide it."""
    text = stdout.strip() or stderr.strip()
    if not text:
        return None

    # Codex --json responses.
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

    # Claude (and similar) human-readable success lines.
    for line in text.splitlines():
        cleaned = line.strip()
        if "✔" in cleaned:
            cleaned = cleaned.split("✔", 1)[-1].strip()
        if cleaned.lower().startswith("successfully"):
            return cleaned
    return None


def print_section(title: str) -> None:
    print()
    print(STYLE.paint(title, STYLE.bold))
    print(STYLE.paint("─" * 36, STYLE.dim))


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


def has_failures(operations: list[Operation]) -> bool:
    return any(operation.action.startswith("Claude validation failed:") for operation in operations)


def _run_operation(root: Path, operation: Operation) -> str | None:
    if operation.path is not None and operation.content is not None:
        codex.write_json(operation.path, operation.content)
        return None
    if operation.action == "sync" and operation.source is not None:
        codex.copy_codex_package(root, operation.source)
        return None
    if operation.action == "sync-claude" and operation.source is not None:
        claude.copy_claude_package(root, operation.source)
        return None
    if operation.action == "sync-cursor" and operation.source is not None and operation.path is not None:
        cursor.copy_skill(operation.source, operation.path)
        return None
    if operation.command:
        result = subprocess.run(operation.command, check=False, text=True, capture_output=True)
        if result.returncode != 0:
            detail = (result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}")
            raise RuntimeError(detail)
        return summarize_command_output(result.stdout, result.stderr)
    return None


def apply_operations(root: Path, operations: list[Operation]) -> None:
    print_section("Applying")
    current_platform: str | None = None
    for operation in operations:
        platform = operation_platform(operation)
        if platform != current_platform:
            current_platform = platform
            print(STYLE.paint(platform.capitalize(), STYLE.magenta, STYLE.bold))

        label = describe_operation(root, operation)
        try:
            detail = _run_operation(root, operation)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"  {STYLE.paint('✖', STYLE.red)} {label}")
            print(f"    {STYLE.paint(str(exc), STYLE.red)}")
            raise SystemExit(1) from exc

        print(f"  {STYLE.paint('✔', STYLE.green)} {label}")
        if detail:
            print(f"    {STYLE.paint(detail, STYLE.dim)}")


def print_done(operations: list[Operation]) -> None:
    counts: dict[str, int] = {}
    for operation in operations:
        platform = operation_platform(operation)
        counts[platform] = counts.get(platform, 0) + 1
    parts = [f"{name} {count}" for name, count in counts.items()]
    summary = " · ".join(parts) if parts else "nothing to do"
    print()
    print(f"{STYLE.paint('✔ Done', STYLE.green, STYLE.bold)}  {STYLE.paint(summary, STYLE.dim)}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = repo_root()
    supported_platforms = implemented_platforms(root)
    args = parse_args(argv, supported_platforms)
    if _wants_interactive(argv, args):
        try:
            args = interactive_fill(root, supported_platforms, args)
        except KeyboardInterrupt:
            print(f"\n{STYLE.paint('Aborted.', STYLE.dim)}")
            return 1
    if args.scope is None:
        args.scope = "repo"
    if args.plugin is None:
        args.plugin = "all"
    args.supported_platforms = supported_platforms

    platforms = target_platforms(args)
    try:
        operations = build_plan(root, platforms, args.scope, args.plugin, args.generate_only)
    except ValueError as exc:
        print(f"{STYLE.paint('error:', STYLE.red)} {exc}", file=sys.stderr)
        return 2

    print_plan(root, operations)
    if has_failures(operations):
        return 1

    if args.dry_run:
        print(f"\n{STYLE.paint('Dry run only; no files written.', STYLE.yellow)}")
        return 0

    write_operations = [operation for operation in operations if operation.path is not None or operation.command]
    if not write_operations:
        print(f"\n{STYLE.paint('No file writes to apply.', STYLE.dim)}")
        return 0

    apply_operations(root, write_operations)
    print_done(write_operations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
