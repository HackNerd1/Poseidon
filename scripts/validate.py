#!/usr/bin/env python3
"""Validate Poseidon skill metadata and platform manifests."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from adapters import claude, codex
from platform_matrix import implemented_platforms


SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKILL_FRONTMATTER_KEYS = {"name", "description"}
CODEX_HOOK_EVENTS = {
    "SessionStart",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStart",
    "SubagentStop",
    "Stop",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def hook_intent_files(plugin_dir: Path) -> list[Path]:
    intents_dir = plugin_dir / "hooks" / "intents"
    if not intents_dir.exists():
        return []
    return sorted(intents_dir.glob("*.yaml"))


def hook_intent_context(root: Path, plugin_dir: Path) -> dict[str, Any]:
    manifest = codex.generate_plugin_manifest(plugin_dir)
    plugin_name = str(manifest["name"])
    plugin_version = str(manifest["version"])
    codex_cache_root = codex.cache_plugin_root(plugin_name, plugin_version, root)
    codex_cache_root_windows = codex.cache_plugin_root_windows(plugin_name, plugin_version, root)
    claude_plugin_root = "${CLAUDE_PLUGIN_ROOT}"
    return {
        "repo_root": str(root),
        "plugin_dir": str(plugin_dir),
        "plugin_name": plugin_name,
        "plugin_version": plugin_version,
        "marketplace_name": codex.marketplace_name(root),
        "codex_cache_plugin_root": codex_cache_root,
        "codex_cache_plugin_root_windows": codex_cache_root_windows,
        "claude_plugin_root": claude_plugin_root,
        "PLUGIN_NAME": plugin_name,
        "PLUGIN_VERSION": plugin_version,
        "MARKETPLACE_NAME": codex.marketplace_name(root),
        "CODEX_CACHE_PLUGIN_ROOT": codex_cache_root,
        "CODEX_CACHE_PLUGIN_ROOT_WINDOWS": codex_cache_root_windows,
        "CLAUDE_PLUGIN_ROOT": claude_plugin_root,
        "plugin": {
            "name": plugin_name,
            "version": plugin_version,
        },
        "codex": {
            "cache_plugin_root": codex_cache_root,
            "cache_plugin_root_windows": codex_cache_root_windows,
        },
        "claude": {
            "plugin_root": claude_plugin_root,
        },
        "placeholders": {
            "PLUGIN_NAME": plugin_name,
            "PLUGIN_VERSION": plugin_version,
            "MARKETPLACE_NAME": codex.marketplace_name(root),
            "CODEX_CACHE_PLUGIN_ROOT": codex_cache_root,
            "CODEX_CACHE_PLUGIN_ROOT_WINDOWS": codex_cache_root_windows,
            "CLAUDE_PLUGIN_ROOT": claude_plugin_root,
        },
    }


def render_hook_intent_hooks(
    root: Path,
    plugin_dir: Path,
    platform: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    intent_files = hook_intent_files(plugin_dir)
    if not intent_files:
        return None, []

    intents_dir = plugin_dir / "hooks" / "intents"
    try:
        hook_intents = importlib.import_module("hook_intents")
    except Exception as exc:
        return None, [f"{intents_dir}: unable to load hook_intents renderer: {exc}"]

    try:
        rendered = hook_intents.render_platform_hooks(
            plugin_dir,
            platform,
            hook_intent_context(root, plugin_dir),
        )
    except Exception as exc:
        return None, [f"{intents_dir}: unable to render {platform} hooks from intents: {exc}"]

    if not isinstance(rendered, dict):
        return None, [f"{intents_dir}: rendered {platform} hooks must be a JSON object"]

    try:
        json.dumps(rendered)
    except (TypeError, ValueError) as exc:
        return None, [f"{intents_dir}: rendered {platform} hooks are not JSON serializable: {exc}"]

    return rendered, []


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter delimiter")

    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    raise ValueError("missing closing frontmatter delimiter")


def validate_skills(root: Path) -> list[str]:
    errors: list[str] = []
    skill_files = sorted((root / "plugins").glob("*/skills/*/SKILL.md"))
    for skill_file in skill_files:
        try:
            fields = parse_frontmatter(skill_file)
        except ValueError as exc:
            errors.append(f"{skill_file}: {exc}")
            continue

        name = fields.get("name", "")
        description = fields.get("description", "")
        unexpected = sorted(set(fields) - SKILL_FRONTMATTER_KEYS)
        if unexpected:
            errors.append(
                f"{skill_file}: unsupported frontmatter field(s): {', '.join(unexpected)}"
            )
        if not name:
            errors.append(f"{skill_file}: missing frontmatter field 'name'")
        elif not SKILL_NAME_PATTERN.match(name):
            errors.append(f"{skill_file}: skill name must be lowercase hyphen-case: {name}")

        if not description:
            errors.append(f"{skill_file}: missing frontmatter field 'description'")
        elif len(description) > 1024:
            errors.append(f"{skill_file}: description exceeds 1024 characters")

    return errors


def validate_codex_hooks(path: Path, hooks_config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    hooks = hooks_config.get("hooks")
    if not isinstance(hooks, dict):
        return [f"{path}: missing hooks object"]

    for event, groups in hooks.items():
        if event not in CODEX_HOOK_EVENTS:
            errors.append(f"{path}: unsupported Codex hook event '{event}'")
        if not isinstance(groups, list):
            errors.append(f"{path}: hook event '{event}' must be an array")
            continue
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                errors.append(f"{path}: hook group {event}[{group_index}] must be an object")
                continue
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                errors.append(f"{path}: hook group {event}[{group_index}] missing hooks array")
                continue
            for handler_index, handler in enumerate(handlers):
                location = f"{path}: hook {event}[{group_index}].hooks[{handler_index}]"
                if not isinstance(handler, dict):
                    errors.append(f"{location} must be an object")
                    continue
                if handler.get("type") != "command":
                    errors.append(f"{location} must use type 'command'")
                if handler.get("async") is True:
                    errors.append(f"{location} must not use async: true; Codex skips async hooks")
                command = str(handler.get("command") or "")
                command_windows = str(handler.get("commandWindows") or "")
                combined_command = f"{command}\n{command_windows}"
                if "${CLAUDE_PLUGIN_ROOT}" in combined_command:
                    errors.append(f"{location} must not reference CLAUDE_PLUGIN_ROOT")
                if not command:
                    errors.append(f"{location} missing command")
                if "notify.py" in combined_command:
                    if "--quiet" not in combined_command:
                        errors.append(f"{location} notification hooks must use --quiet")
                    if "--best-effort" not in combined_command:
                        errors.append(f"{location} notification hooks must use --best-effort")

    return errors


def validate_codex(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        metadata = codex.read_metadata(root)
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as exc:
        errors.append(f"Invalid Codex plugin metadata {codex.metadata_path(root)}: {exc}")
        return errors

    plugin_dirs = codex.discover_plugin_dirs(root)
    if not plugin_dirs:
        errors.append("No plugins discovered under plugins/*")
        return errors
    metadata_plugins = metadata.get("plugins")
    if not isinstance(metadata_plugins, dict):
        errors.append(f"{codex.metadata_path(root)}: plugins must be an object")
        return errors

    for plugin_dir in plugin_dirs:
        if plugin_dir.name not in metadata_plugins:
            errors.append(f"{codex.metadata_path(root)}: missing metadata for plugin '{plugin_dir.name}'")

        source_manifest = codex.plugin_manifest_path(plugin_dir)
        if source_manifest.exists():
            errors.append(f"{source_manifest}: source Codex manifests are generated; keep metadata in {codex.PLUGIN_METADATA}")
        for generated_hook_source in (
            plugin_dir / "hooks" / "hooks.json",
            plugin_dir / "hooks" / "codex",
            plugin_dir / "hooks" / "claude",
        ):
            if generated_hook_source.is_file() or (
                generated_hook_source.is_dir() and any(generated_hook_source.rglob("*"))
            ):
                errors.append(
                    f"{generated_hook_source}: platform hook configs are generated; "
                    "keep canonical hooks in hooks/intents/*.yaml"
                )

    plugin_names = {plugin_dir.name for plugin_dir in plugin_dirs}
    extra_metadata = set(metadata_plugins) - plugin_names
    if extra_metadata:
        errors.append(
            f"{codex.metadata_path(root)}: metadata references unknown plugin(s): "
            f"{', '.join(sorted(extra_metadata))}"
        )

    marketplace_path = codex.marketplace_path(root)
    if marketplace_path.exists():
        try:
            marketplace = read_json(marketplace_path)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid Codex marketplace {marketplace_path}: {exc}")
            return errors

        expected_marketplace = codex.generate_marketplace(root, plugin_dirs)
        if not codex.json_equal(marketplace, expected_marketplace):
            errors.append(f"{marketplace_path}: generated content is not in sync with plugin manifests")

        entries = marketplace.get("plugins")
        if not isinstance(entries, list):
            errors.append(f"{marketplace_path}: plugins must be an array")
            return errors

        plugin_names = {plugin_dir.name for plugin_dir in plugin_dirs}
        entry_names = set()
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"{marketplace_path}: every plugin entry must be an object")
                continue
            name = entry.get("name")
            entry_names.add(name)
            if name not in plugin_names:
                errors.append(f"{marketplace_path}: entry references unknown plugin '{name}'")
            source = entry.get("source")
            if source != {"source": "local", "path": codex.package_source_path(str(name))}:
                errors.append(f"{marketplace_path}: invalid source for plugin '{name}'")
            policy = entry.get("policy")
            if not isinstance(policy, dict):
                errors.append(f"{marketplace_path}: missing policy for plugin '{name}'")
            else:
                if policy.get("installation") != "AVAILABLE":
                    errors.append(f"{marketplace_path}: plugin '{name}' installation policy must be AVAILABLE")
                if policy.get("authentication") != "ON_INSTALL":
                    errors.append(f"{marketplace_path}: plugin '{name}' authentication policy must be ON_INSTALL")
            if not entry.get("category"):
                errors.append(f"{marketplace_path}: plugin '{name}' missing category")

        missing = plugin_names - entry_names
        if missing:
            errors.append(f"{marketplace_path}: missing marketplace entries for {', '.join(sorted(missing))}")

    for plugin_dir in plugin_dirs:
        package_dir = codex.package_plugin_path(root, plugin_dir.name)
        if not package_dir.exists():
            continue
        package_manifest = package_dir / codex.PLUGIN_MANIFEST
        if not package_manifest.exists():
            errors.append(f"Missing Codex package manifest: {package_manifest}")
        else:
            try:
                actual_manifest = read_json(package_manifest)
                expected_manifest = codex.generate_plugin_manifest(plugin_dir)
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"Invalid Codex package manifest {package_manifest}: {exc}")
            else:
                if actual_manifest.get("name") != plugin_dir.name:
                    errors.append(
                        f"{package_manifest}: name must match plugin folder '{plugin_dir.name}'"
                    )
                if actual_manifest.get("skills") != "./skills/":
                    errors.append(f"{package_manifest}: skills must be './skills/'")
                if not isinstance(actual_manifest.get("interface"), dict):
                    errors.append(f"{package_manifest}: missing interface metadata object")
                if not codex.json_equal(actual_manifest, expected_manifest):
                    errors.append(
                        f"{package_manifest}: generated content is not in sync with {codex.PLUGIN_METADATA}"
                    )
        default_hooks = package_dir / "hooks" / "hooks.json"
        intent_files = hook_intent_files(plugin_dir)
        expected_source = "hooks/codex/hooks.json"
        if intent_files:
            expected_source = "hooks/intents/*.yaml"
            expected_hooks, render_errors = render_hook_intent_hooks(root, plugin_dir, "codex")
            errors.extend(render_errors)
            if expected_hooks is not None:
                errors.extend(validate_codex_hooks(plugin_dir / "hooks" / "intents", expected_hooks))
        else:
            expected_hooks = codex.render_codex_hooks(plugin_dir)
        if default_hooks.exists():
            try:
                actual_hooks = read_json(default_hooks)
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"Invalid Codex hooks {default_hooks}: {exc}")
                continue
            if expected_hooks is None:
                if not intent_files:
                    errors.append(f"{default_hooks}: default hooks must come from {expected_source}")
            elif not codex.json_equal(actual_hooks, expected_hooks):
                errors.append(f"{default_hooks}: generated hooks are not in sync with {expected_source}")
            errors.extend(validate_codex_hooks(default_hooks, actual_hooks))
        elif expected_hooks is not None:
            errors.append(f"Missing generated Codex hooks: {default_hooks}")

    return errors


def validate_claude_hook_intents(root: Path) -> list[str]:
    errors: list[str] = []
    for plugin_dir in claude.discover_plugin_dirs(root):
        if not hook_intent_files(plugin_dir):
            continue
        rendered_hooks, render_errors = render_hook_intent_hooks(root, plugin_dir, "claude")
        if rendered_hooks is None:
            errors.extend(render_errors)
            continue
        hooks = rendered_hooks.get("hooks")
        if not isinstance(hooks, dict):
            errors.append(f"{plugin_dir / 'hooks' / 'intents'}: rendered claude hooks missing hooks object")
            continue

        package_hooks = claude.package_plugin_path(root, plugin_dir.name) / "hooks" / "hooks.json"
        if not package_hooks.exists():
            continue
        try:
            actual_hooks = read_json(package_hooks)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid Claude hooks {package_hooks}: {exc}")
            continue
        if not codex.json_equal(actual_hooks, rendered_hooks):
            errors.append(f"{package_hooks}: generated hooks are not in sync with hooks/intents/*.yaml")
    return errors


def validate_claude(root: Path) -> list[str]:
    errors = claude.validate(root)
    errors.extend(validate_claude_hook_intents(root))
    return errors


def parse_args(argv: list[str], supported_platforms: tuple[str, ...]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Poseidon platform packaging.")
    parser.add_argument("--platform", choices=supported_platforms, help="Platform to validate.")
    parser.add_argument("--all", action="store_true", help="Validate every supported platform.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    supported_platforms = implemented_platforms(root)
    args = parse_args(list(sys.argv[1:] if argv is None else argv), supported_platforms)
    if not args.platform and not args.all:
        raise SystemExit("Specify --platform codex, --platform claude, or --all.")

    errors = validate_skills(root)
    platforms = supported_platforms if args.all else (args.platform,)
    for platform in platforms:
        if platform == "codex":
            errors.extend(validate_codex(root))
        elif platform == "claude":
            errors.extend(validate_claude(root))

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    selected = "all platforms" if args.all else args.platform
    print(f"Validation passed for {selected}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
