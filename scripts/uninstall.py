#!/usr/bin/env python3
"""Poseidon platform matrix uninstaller (full reverse of install)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from adapters import claude, codex, cursor
from platform_matrix import implemented_platforms
from shared import (
    SCOPES,
    STYLE,
    Operation,
    describe_operation,
    effective_scope,
    interactive_fill,
    operation_platform,
    print_done,
    print_plan,
    print_section,
    repo_root,
    summarize_command_output,
    target_platforms,
    validate_scope,
    wants_interactive,
)


_INTERACTIVE_OK_FLAGS = frozenset(
    {
        "--interactive",
        "--dry-run",
        "--scope",
        "--plugin",
        "--mode",
    }
)


def parse_args(argv: list[str], supported_platforms: tuple[str, ...]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Uninstall Poseidon plugins from agent platforms.")
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
            "Install scope to remove for the selected mode: repo or user. Default: repo."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("plugin", "agent", "agents"),
        default=None,
        help=(
            "Uninstall mode matching install.py: plugin, agent, or agents. Default: plugin."
        ),
    )
    parser.add_argument(
        "--plugin",
        default=None,
        help="Plugin name, comma-separated list, or 'all'. Default: all.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without changing anything.")
    return parser.parse_args(argv)


def _removing_all_plugins(root: Path, plugin: str) -> bool:
    selected = codex.select_plugin_dirs(root, plugin)
    discovered = codex.discover_plugin_dirs(root)
    return bool(discovered) and len(selected) == len(discovered)


def codex_uninstall_plan(root: Path, scope: str, plugin: str, mode: str = "plugin") -> list[Operation]:
    validate_scope("codex", scope)
    selected = codex.select_plugin_dirs(root, plugin)
    operations: list[Operation] = []
    if mode != "plugin":
        return [
            Operation("delete", codex.skill_target_path(skill_dir, scope, mode), source=skill_dir)
            for plugin_dir in selected
            for skill_dir in cursor.discover_skill_dirs([plugin_dir])
        ]
    marketplace = codex.marketplace_name(root)

    for plugin_dir in selected:
        operations.append(
            Operation(
                "run",
                None,
                command=[
                    "codex",
                    "plugin",
                    "remove",
                    f"{plugin_dir.name}@{marketplace}",
                    "--json",
                ],
            )
        )
        operations.append(
            Operation(
                "delete",
                codex.package_plugin_path(root, plugin_dir.name),
                source=plugin_dir,
            )
        )

    if _removing_all_plugins(root, plugin):
        operations.append(
            Operation(
                "run",
                None,
                command=["codex", "plugin", "marketplace", "remove", marketplace, "--json"],
            )
        )
    return operations


def claude_uninstall_plan(root: Path, scope: str, plugin: str, mode: str = "plugin") -> list[Operation]:
    validate_scope("claude", scope)
    selected = codex.select_plugin_dirs(root, plugin)
    operations: list[Operation] = []
    marketplace = codex.marketplace_name(root)
    claude_scope = "project" if scope == "repo" else scope

    if mode != "plugin":
        return [
            Operation("delete", claude.skill_target_path(skill_dir, scope, mode), source=skill_dir)
            for plugin_dir in selected
            for skill_dir in cursor.discover_skill_dirs([plugin_dir])
        ]

    for plugin_dir in selected:
        operations.append(
            Operation(
                "run",
                None,
                command=[
                    "claude",
                    "plugin",
                    "uninstall",
                    f"{plugin_dir.name}@{marketplace}",
                    "--scope",
                    claude_scope,
                    "-y",
                ],
            )
        )
        operations.append(
            Operation(
                "delete",
                claude.package_plugin_path(root, plugin_dir.name),
                source=plugin_dir,
            )
        )

    if _removing_all_plugins(root, plugin):
        operations.append(
            Operation(
                "run",
                None,
                command=["claude", "plugin", "marketplace", "remove", marketplace],
            )
        )
    return operations


def cursor_uninstall_plan(root: Path, scope: str, plugin: str, mode: str = "plugin") -> list[Operation]:
    validate_scope("cursor", scope)
    plugin_dirs = cursor.select_plugin_dirs(root, plugin)
    operations: list[Operation] = []
    for skill_dir in cursor.discover_skill_dirs(plugin_dirs):
        operations.append(
            Operation(
                "delete",
                cursor.skill_target_path(root, scope, skill_dir, mode),
                source=skill_dir,
            )
        )
    return operations


def build_plan(
    root: Path,
    platforms: list[str],
    scope: str,
    plugin: str,
    mode: str = "plugin",
) -> list[Operation]:
    operations: list[Operation] = []
    multi_platform = len(platforms) > 1
    for platform in platforms:
        platform_scope = effective_scope(platform, scope, multi_platform=multi_platform)
        if platform == "codex":
            operations.extend(codex_uninstall_plan(root, platform_scope, plugin, mode))
        elif platform == "claude":
            operations.extend(claude_uninstall_plan(root, platform_scope, plugin, mode))
        elif platform == "cursor":
            operations.extend(cursor_uninstall_plan(root, platform_scope, plugin, mode))
    unique: list[Operation] = []
    seen: set[tuple[str, str, str]] = set()
    for operation in operations:
        key = (operation.action, str(operation.path), str(operation.source))
        if key not in seen:
            seen.add(key)
            unique.append(operation)
    return unique


def _is_benign_cli_error(detail: str) -> bool:
    text = detail.lower()
    needles = (
        "not installed",
        "not found",
        "no such",
        "does not exist",
        "unknown plugin",
        "unknown marketplace",
        "is not configured",
        "not configured",
        "already removed",
        "no marketplace",
    )
    return any(needle in text for needle in needles)


def _delete_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink(missing_ok=True)


def _run_command(operation: Operation) -> tuple[str | None, bool]:
    """Return (detail, skipped)."""
    if not operation.command:
        return None, False
    result = subprocess.run(operation.command, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        if _is_benign_cli_error(detail):
            summary = summarize_command_output(result.stdout, result.stderr)
            return summary or detail.splitlines()[-1], True
        raise RuntimeError(detail)
    return summarize_command_output(result.stdout, result.stderr), False


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
            if operation.action == "delete" and operation.path is not None:
                missing = not operation.path.exists() and not operation.path.is_symlink()
                if missing:
                    print(f"  {STYLE.paint('–', STYLE.dim)} {label}")
                    print(f"    {STYLE.paint('not present (skipped)', STYLE.dim)}")
                    continue
                _delete_path(operation.path)
                print(f"  {STYLE.paint('✔', STYLE.green)} {label}")
                continue

            detail, skipped = _run_command(operation)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"  {STYLE.paint('✖', STYLE.red)} {label}")
            print(f"    {STYLE.paint(str(exc), STYLE.red)}")
            raise SystemExit(1) from exc

        mark = STYLE.paint("–", STYLE.dim) if skipped else STYLE.paint("✔", STYLE.green)
        print(f"  {mark} {label}")
        if detail:
            suffix = " (skipped)" if skipped else ""
            print(f"    {STYLE.paint(f'{detail}{suffix}', STYLE.dim)}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = repo_root()
    supported_platforms = implemented_platforms(root)
    args = parse_args(argv, supported_platforms)
    if wants_interactive(argv, args, _INTERACTIVE_OK_FLAGS):
        try:
            args = interactive_fill(
                root,
                supported_platforms,
                args,
                title="Poseidon Uninstaller",
                subtitle="platform matrix · interactive teardown",
            )
        except KeyboardInterrupt:
            print(f"\n{STYLE.paint('Aborted.', STYLE.dim)}")
            return 1
    if args.scope is None:
        args.scope = "repo"
    if args.mode is None:
        args.mode = "plugin"
    if args.plugin is None:
        args.plugin = "all"
    args.supported_platforms = supported_platforms

    platforms = target_platforms(args)
    try:
        operations = build_plan(root, platforms, args.scope, args.plugin, args.mode)
    except ValueError as exc:
        print(f"{STYLE.paint('error:', STYLE.red)} {exc}", file=sys.stderr)
        return 2

    print_plan(root, operations)

    if args.dry_run:
        print(f"\n{STYLE.paint('Dry run only; nothing changed.', STYLE.yellow)}")
        return 0

    if not operations:
        print(f"\n{STYLE.paint('Nothing to uninstall.', STYLE.dim)}")
        return 0

    apply_operations(root, operations)
    print_done(operations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
