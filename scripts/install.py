#!/usr/bin/env python3
"""Poseidon platform matrix installer."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adapters import claude, codex
from platform_matrix import implemented_platforms


SCOPES = ("repo", "user")


@dataclass(frozen=True)
class Operation:
    action: str
    path: Path | None
    content: dict[str, Any] | None = None
    command: list[str] | None = None
    source: Path | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args(argv: list[str], supported_platforms: tuple[str, ...]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Poseidon plugins for agent platforms.")
    parser.add_argument("--interactive", action="store_true", help="Run the interactive CLI.")
    parser.add_argument("--platform", choices=supported_platforms, help="Target platform.")
    parser.add_argument("--all", action="store_true", help="Target all supported platforms.")
    parser.add_argument("--scope", choices=SCOPES, default="repo", help="Install scope.")
    parser.add_argument("--plugin", default="all", help="Plugin name, or 'all'.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing files.")
    parser.add_argument("--yes", action="store_true", help="Apply without confirmation.")
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Only write local manifest and marketplace files; do not register, install, or enable plugins.",
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
    scope = prompt_choice(
        "Select install scope",
        [("repo", "Repo-local"), ("user", "User-global")],
        "repo",
    )
    plugin_choices = [("all", "All plugins")]
    plugin_choices.extend((path.name, path.name) for path in codex.discover_plugin_dirs(root))
    plugin = prompt_choice("Select plugin", plugin_choices, "all")
    mode = prompt_choice(
        "Select operation mode",
        [("dry-run", "Dry run"), ("apply", "Apply changes")],
        "dry-run",
    )
    enable_codex = "yes"
    if platform in {"codex", "all"}:
        enable_codex = prompt_choice(
            "Install and enable Codex plugins after generating files",
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
        generate_only=enable_codex == "no",
    )


def target_platforms(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(args.supported_platforms)
    if args.platform:
        return [args.platform]
    raise SystemExit("Specify --platform, --all, or run with no arguments for interactive mode.")


def codex_plan(root: Path, scope: str, plugin: str, generate_only: bool) -> list[Operation]:
    if scope != "repo":
        return [
            Operation(
                "Codex user-global install is reserved for a later phase; use --scope repo for generation.",
                None,
            )
        ]

    plugin_dirs = codex.select_plugin_dirs(root, plugin)
    operations: list[Operation] = []
    for plugin_dir in plugin_dirs:
        operations.append(
            Operation(
                "write",
                codex.plugin_manifest_path(plugin_dir),
                codex.generate_plugin_manifest(plugin_dir),
            )
        )

    marketplace = (
        codex.generate_marketplace(root, codex.discover_plugin_dirs(root))
        if plugin in (None, "", "all")
        else codex.generate_marketplace_update(root, plugin_dirs)
    )
    operations.append(
        Operation(
            "write",
            codex.marketplace_path(root),
            marketplace,
        )
    )
    for plugin_dir in plugin_dirs:
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
        for plugin_dir in plugin_dirs:
            operations.append(
                Operation(
                    "run",
                    None,
                    command=[
                        "codex",
                        "plugin",
                        "add",
                        f"{plugin_dir.name}@{codex.MARKETPLACE_NAME}",
                        "--json",
                    ],
                )
            )
    return operations


def claude_plan(root: Path, scope: str, plugin: str) -> list[Operation]:
    errors = claude.validate(root, plugin)
    if errors:
        return [Operation(f"Claude validation failed: {error}", None) for error in errors]
    message = "Claude support is validation-only in this phase; existing .claude-plugin files are unchanged."
    if scope == "user":
        message += " User-global installation is reserved for a later phase."
    return [Operation(message, None)]


def build_plan(
    root: Path,
    platforms: list[str],
    scope: str,
    plugin: str,
    generate_only: bool,
) -> list[Operation]:
    operations: list[Operation] = []
    for platform in platforms:
        if platform == "codex":
            operations.extend(codex_plan(root, scope, plugin, generate_only))
        elif platform == "claude":
            operations.extend(claude_plan(root, scope, plugin))
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
            rel = operation.path.relative_to(root)
            if operation.source:
                print(f"  - {operation.action} {operation.source.relative_to(root)} -> {rel}")
            else:
                print(f"  - {operation.action} {rel}")


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
            print(f"  - {operation.path.relative_to(root)}")
        elif operation.command:
            print(f"  - {' '.join(operation.command)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
