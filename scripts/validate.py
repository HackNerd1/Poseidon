#!/usr/bin/env python3
"""Validate Poseidon skill metadata and platform manifests."""

from __future__ import annotations

import argparse
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
    plugin_dirs = codex.discover_plugin_dirs(root)
    if not plugin_dirs:
        errors.append("No plugins discovered under plugins/*")
        return errors

    for plugin_dir in plugin_dirs:
        expected = codex.generate_plugin_manifest(plugin_dir)
        manifest_path = codex.plugin_manifest_path(plugin_dir)
        if not manifest_path.exists():
            errors.append(f"Missing Codex manifest: {manifest_path}")
            continue
        try:
            actual = read_json(manifest_path)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid Codex manifest {manifest_path}: {exc}")
            continue

        if actual.get("name") != plugin_dir.name:
            errors.append(f"{manifest_path}: name must match plugin folder '{plugin_dir.name}'")
        if actual.get("skills") != "./skills/":
            errors.append(f"{manifest_path}: skills must be './skills/'")
        if not isinstance(actual.get("interface"), dict):
            errors.append(f"{manifest_path}: missing interface metadata object")
        if not codex.json_equal(actual, expected):
            errors.append(f"{manifest_path}: generated content is not in sync with Claude metadata")

    marketplace_path = codex.marketplace_path(root)
    if not marketplace_path.exists():
        errors.append(f"Missing Codex marketplace: {marketplace_path}")
        return errors

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
            errors.append(f"Missing generated Codex package: {package_dir}")
            continue
        package_manifest = package_dir / codex.PLUGIN_MANIFEST
        if not package_manifest.exists():
            errors.append(f"Missing Codex package manifest: {package_manifest}")
        default_hooks = package_dir / "hooks" / "hooks.json"
        expected_hooks = codex.render_codex_hooks(plugin_dir)
        if default_hooks.exists():
            try:
                actual_hooks = read_json(default_hooks)
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"Invalid Codex hooks {default_hooks}: {exc}")
                continue
            if expected_hooks is None:
                errors.append(f"{default_hooks}: default hooks must come from hooks/codex/hooks.json")
            elif not codex.json_equal(actual_hooks, expected_hooks):
                errors.append(f"{default_hooks}: generated hooks are not in sync with hooks/codex/hooks.json")
            errors.extend(validate_codex_hooks(default_hooks, actual_hooks))
        elif expected_hooks is not None:
            errors.append(f"Missing generated Codex hooks: {default_hooks}")

    return errors


def validate_claude(root: Path) -> list[str]:
    return claude.validate(root)


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
