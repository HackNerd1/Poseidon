#!/usr/bin/env python3
"""Poseidon platform matrix installer."""

from __future__ import annotations

import argparse
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


@dataclass(frozen=True)
class Operation:
    action: str
    path: Path | None
    content: dict[str, Any] | None = None
    command: list[str] | None = None
    source: Path | None = None


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
    parser.add_argument("--platform", choices=supported_platforms, help="Target platform.")
    parser.add_argument("--all", action="store_true", help="Target all supported platforms.")
    parser.add_argument(
        "--scope",
        choices=SCOPES,
        default="repo",
        help=(
            "Install scope. Codex/Claude support repo only; "
            "Cursor supports repo (.cursor/skills) and user (~/.cursor/skills)."
        ),
    )
    parser.add_argument("--plugin", default="all", help="Plugin name, or 'all'.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing files.")
    parser.add_argument("--yes", action="store_true", help="Apply without confirmation.")
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help=(
            "Only write local package/manifest files; do not register, install, or enable "
            "plugins via platform CLIs. Cursor still copies skills (copy is the install)."
        ),
    )
    return parser.parse_args(argv)


def prompt_choice(label: str, choices: list[tuple[str, str]], default: str) -> str:
    print(f"\n{label}")
    for index, (value, title) in enumerate(choices, start=1):
        suffix = " (default)" if value == default else ""
        print(f"  {index}. {title}{suffix}")
    raw = input("> ").strip()
    if not raw:
        return default
    if raw.isdigit() and 1 <= int(raw) <= len(choices):
        return choices[int(raw) - 1][0]
    values = {value for value, _title in choices}
    if raw in values:
        return raw
    raise SystemExit(f"Invalid choice: {raw}")


def interactive_args(root: Path, supported_platforms: tuple[str, ...]) -> argparse.Namespace:
    print("Poseidon Installer")
    platform_choices = [(platform, platform.capitalize()) for platform in supported_platforms]
    platform_choices.append(("all", "All supported platforms"))
    platform = prompt_choice(
        "Select target platform",
        platform_choices,
        "codex",
    )
    selected_platforms = list(supported_platforms) if platform == "all" else [platform]
    plugin_choices = [("all", "All plugins")]
    plugin_choices.extend((path.name, path.name) for path in codex.discover_plugin_dirs(root))
    plugin = prompt_choice("Select plugin", plugin_choices, "all")

    scope = "repo"
    if "cursor" in selected_platforms:
        scope_choices = [
            ("repo", "Repo (.cursor/skills)"),
            ("user", "User (~/.cursor/skills)"),
        ]
        # When installing multiple platforms, keep Codex/Claude on repo and only
        # offer Cursor scope when Cursor is the sole target.
        if selected_platforms == ["cursor"]:
            scope = prompt_choice("Select Cursor install scope", scope_choices, "repo")

    mode = prompt_choice(
        "Select operation mode",
        [("dry-run", "Dry run"), ("apply", "Apply changes")],
        "dry-run",
    )
    enable_cli = "yes"
    if any(name in {"codex", "claude"} for name in selected_platforms):
        enable_cli = prompt_choice(
            "Install/enable plugins via platform CLI after generating files",
            [("yes", "Yes"), ("no", "No, generate files only")],
            "yes",
        )
    return argparse.Namespace(
        interactive=True,
        platform=None if platform == "all" else platform,
        all=platform == "all",
        scope=scope,
        plugin=plugin,
        dry_run=mode == "dry-run",
        yes=False,
        generate_only=enable_cli == "no",
    )


def target_platforms(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(args.supported_platforms)
    if args.platform:
        return [args.platform]
    raise SystemExit("Specify --platform, --all, or run with no arguments for interactive mode.")


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


def print_plan(root: Path, operations: list[Operation]) -> None:
    print("\nPlan:")
    if not operations:
        print("  - No operations")
        return
    for operation in operations:
        if operation.path is None:
            if operation.command:
                print(f"  - {operation.action} {' '.join(operation.command)}")
            else:
                print(f"  - {operation.action}")
        else:
            path_text = display_path(root, operation.path)
            if operation.source:
                print(f"  - {operation.action} {display_path(root, operation.source)} -> {path_text}")
            else:
                print(f"  - {operation.action} {path_text}")


def has_failures(operations: list[Operation]) -> bool:
    return any(operation.action.startswith("Claude validation failed:") for operation in operations)


def confirm() -> bool:
    answer = input("\nProceed? yes/no: ").strip().lower()
    return answer in {"y", "yes"}


def apply_operations(operations: list[Operation]) -> None:
    for operation in operations:
        if operation.path is not None and operation.content is not None:
            codex.write_json(operation.path, operation.content)
            continue
        if operation.action == "sync" and operation.source is not None:
            codex.copy_codex_package(repo_root(), operation.source)
            continue
        if operation.action == "sync-claude" and operation.source is not None:
            claude.copy_claude_package(repo_root(), operation.source)
            continue
        if operation.action == "sync-cursor" and operation.source is not None and operation.path is not None:
            cursor.copy_skill(operation.source, operation.path)
            continue
        if operation.command:
            result = subprocess.run(operation.command, check=True, text=True, capture_output=True)
            output = result.stdout.strip()
            if output:
                print(output)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = repo_root()
    supported_platforms = implemented_platforms(root)
    args = (
        interactive_args(root, supported_platforms)
        if not argv or "--interactive" in argv
        else parse_args(argv, supported_platforms)
    )
    args.supported_platforms = supported_platforms

    platforms = target_platforms(args)
    try:
        operations = build_plan(root, platforms, args.scope, args.plugin, args.generate_only)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print_plan(root, operations)
    if has_failures(operations):
        return 1

    if args.dry_run:
        print("\nDry run only; no files written.")
        return 0

    write_operations = [operation for operation in operations if operation.path is not None or operation.command]
    if not write_operations:
        print("\nNo file writes to apply.")
        return 0

    if not args.yes and not confirm():
        print("Aborted.")
        return 1

    apply_operations(write_operations)
    print("\nApplied:")
    for operation in write_operations:
        if operation.path is not None:
            print(f"  - {display_path(root, operation.path)}")
        elif operation.command:
            print(f"  - {' '.join(operation.command)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
