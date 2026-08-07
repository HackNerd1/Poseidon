"""Shared constants and CLI argument helpers for the platform matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters import codex
from shared.ui import print_banner, select_choice, select_multiple


SCOPES = ("repo", "user")
SUPPORTED_SCOPES = {
    "codex": ("repo",),
    "claude": ("repo",),
    "cursor": ("repo", "user"),
}


def repo_root() -> Path:
    # shared/ -> scripts/ -> repo root
    return Path(__file__).resolve().parents[2]


def encode_plugin_arg(selected: list[str], all_names: list[str]) -> str:
    if not selected or set(selected) == set(all_names):
        return "all"
    return ",".join(selected)


def encode_platform_arg(
    selected: list[str],
    supported: tuple[str, ...] | list[str],
) -> tuple[bool, str | None]:
    """Return (all_flag, platform_arg) for selected platforms."""
    if not selected or set(selected) == set(supported):
        return True, None
    return False, ",".join(selected)


def wants_interactive(
    argv: list[str],
    args: argparse.Namespace,
    ok_flags: frozenset[str],
) -> bool:
    if args.interactive or not argv:
        return True
    if args.platform or args.all:
        return False
    tokens = [token for token in argv if token.startswith("-")]
    for token in tokens:
        name = token.split("=", 1)[0]
        if name not in ok_flags and name not in {"-h", "--help"}:
            return False
    return True


def interactive_fill(
    root: Path,
    supported_platforms: tuple[str, ...],
    args: argparse.Namespace,
    *,
    title: str = "Poseidon Installer",
    subtitle: str = "platform matrix · interactive setup",
) -> argparse.Namespace:
    """Prompt for missing matrix choices; CLI modifiers are preserved."""
    print_banner(title=title, subtitle=subtitle)

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

    selected = set(names)
    return [name for name in supported if name in selected]


def validate_scope(platform: str, scope: str) -> None:
    if scope not in SUPPORTED_SCOPES.get(platform, SCOPES):
        supported = ", ".join(SUPPORTED_SCOPES.get(platform, SCOPES))
        raise ValueError(
            f"{platform.capitalize()} does not support --scope {scope}; "
            f"supported scope: {supported}."
        )


def effective_scope(platform: str, scope: str, *, multi_platform: bool) -> str:
    supported = SUPPORTED_SCOPES.get(platform, SCOPES)
    if scope in supported:
        return scope
    if multi_platform and "repo" in supported:
        # --all with Cursor user scope still installs Codex/Claude at repo scope.
        return "repo"
    validate_scope(platform, scope)
    return scope
