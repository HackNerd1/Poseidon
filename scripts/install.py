#!/usr/bin/env python3
"""Poseidon platform matrix installer."""

from __future__ import annotations

import argparse
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
        "--generate-only",
        "--yes",
        "--scope",
        "--plugin",
    }
)


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
            detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = repo_root()
    supported_platforms = implemented_platforms(root)
    args = parse_args(argv, supported_platforms)
    if wants_interactive(argv, args, _INTERACTIVE_OK_FLAGS):
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
