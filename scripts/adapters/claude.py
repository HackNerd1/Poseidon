"""Claude plugin generation and validation helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import hook_intents

from adapters import codex


PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
MARKETPLACE_PATH = ".claude-plugin/marketplace.json"
PACKAGE_ROOT = ".claude/generated/plugins"


def discover_plugin_dirs(repo_root: Path) -> list[Path]:
    return codex.discover_plugin_dirs(repo_root)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    codex.write_json(path, data)


def package_root(repo_root: Path) -> Path:
    return repo_root / PACKAGE_ROOT


def package_plugin_path(repo_root: Path, plugin_name: str) -> Path:
    return package_root(repo_root) / plugin_name


def package_source_path(plugin_name: str) -> str:
    return f"./{PACKAGE_ROOT}/{plugin_name}"


def plugin_manifest_path(plugin_dir: Path) -> Path:
    return plugin_dir / PLUGIN_MANIFEST


def marketplace_path(repo_root: Path) -> Path:
    return repo_root / MARKETPLACE_PATH


def generate_plugin_manifest(plugin_dir: Path) -> dict[str, Any]:
    metadata = codex.plugin_metadata(plugin_dir)
    return {
        "name": plugin_dir.name,
        "version": str(metadata.get("version") or "0.1.0"),
        "description": str(metadata.get("description") or ""),
        "author": metadata.get("author") or {"name": "Poseidon"},
        "license": str(metadata.get("license") or "MIT"),
        "keywords": list(metadata.get("keywords") or []),
        "skills": ["./skills/"],
    }


def generate_marketplace_entry(plugin_dir: Path) -> dict[str, Any]:
    metadata = codex.plugin_metadata(plugin_dir)
    keywords = list(metadata.get("keywords") or [])
    return {
        "name": plugin_dir.name,
        "source": package_source_path(plugin_dir.name),
        "description": str(metadata.get("description") or ""),
        "version": str(metadata.get("version") or "0.1.0"),
        "category": str(metadata.get("category") or "Productivity").lower(),
        "tags": keywords,
    }


def generate_marketplace(repo_root: Path, plugin_dirs: list[Path] | None = None) -> dict[str, Any]:
    if plugin_dirs is None:
        plugin_dirs = discover_plugin_dirs(repo_root)
    marketplace = codex.marketplace_metadata(repo_root)
    return {
        "name": str(marketplace.get("name") or codex.DEFAULT_MARKETPLACE_NAME),
        "owner": marketplace.get("owner") or {"name": "Poseidon"},
        "metadata": {
            "description": str(marketplace.get("description") or ""),
        },
        "plugins": [generate_marketplace_entry(plugin_dir) for plugin_dir in plugin_dirs],
    }


def hook_intent_context(plugin_dir: Path) -> dict[str, str]:
    return {
        "CLAUDE_PLUGIN_ROOT": "${CLAUDE_PLUGIN_ROOT}",
    }


def render_claude_hooks(plugin_dir: Path) -> dict[str, Any] | None:
    return hook_intents.render_platform_hooks(
        plugin_dir,
        "claude",
        hook_intent_context(plugin_dir),
    )


def render_claude_hooks_template(plugin_dir: Path, target: Path) -> None:
    hooks = render_claude_hooks(plugin_dir)
    if hooks is None:
        return
    write_json(target / "hooks" / "hooks.json", hooks)


def copy_claude_package(repo_root: Path, plugin_dir: Path) -> Path:
    target = package_plugin_path(repo_root, plugin_dir.name)
    if target.exists():
        shutil.rmtree(target)

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {".codex-plugin", ".claude-plugin", "__pycache__"}
        if Path(directory) == plugin_dir / "hooks" and "codex" in names:
            ignored.add("codex")
        if Path(directory) == plugin_dir / "hooks" and "claude" in names:
            ignored.add("claude")
        if Path(directory) == plugin_dir / "hooks" and "intents" in names:
            ignored.add("intents")
        return ignored.intersection(names)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(plugin_dir, target, ignore=ignore)
    write_json(target / PLUGIN_MANIFEST, generate_plugin_manifest(plugin_dir))
    render_claude_hooks_template(plugin_dir, target)
    return target


def validate(repo_root: Path, plugin: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        metadata = codex.read_metadata(repo_root)
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as exc:
        return [f"Invalid plugin metadata {codex.metadata_path(repo_root)}: {exc}"]

    plugin_dirs = discover_plugin_dirs(repo_root)
    if plugin not in (None, "", "all"):
        plugin_dirs = [path for path in plugin_dirs if path.name == plugin]
        if not plugin_dirs:
            errors.append(f"Unknown plugin '{plugin}'")
            return errors

    metadata_plugins = metadata.get("plugins")
    if not isinstance(metadata_plugins, dict):
        return [f"{codex.metadata_path(repo_root)}: plugins must be an object"]

    extra_metadata = set(metadata_plugins) - {
        path.name for path in (repo_root / "plugins").iterdir() if path.is_dir()
    }
    if extra_metadata:
        errors.append(
            f"{codex.metadata_path(repo_root)}: metadata references unknown plugin(s): "
            f"{', '.join(sorted(extra_metadata))}"
        )

    for plugin_dir in plugin_dirs:
        source_manifest = plugin_manifest_path(plugin_dir)
        if source_manifest.exists():
            errors.append(
                f"{source_manifest}: source Claude manifests are generated; "
                f"keep metadata in {codex.PLUGIN_METADATA}"
            )

        package_dir = package_plugin_path(repo_root, plugin_dir.name)
        if not package_dir.exists():
            continue
        package_manifest = package_dir / PLUGIN_MANIFEST
        if not package_manifest.exists():
            errors.append(f"Missing generated Claude manifest: {package_manifest}")
            continue
        try:
            actual = read_json(package_manifest)
            expected = generate_plugin_manifest(plugin_dir)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid Claude manifest {package_manifest}: {exc}")
            continue
        if not codex.json_equal(actual, expected):
            errors.append(
                f"{package_manifest}: generated content is not in sync with {codex.PLUGIN_METADATA}"
            )

    marketplace = repo_root / MARKETPLACE_PATH
    if marketplace.exists():
        try:
            actual_marketplace = read_json(marketplace)
            expected_marketplace = generate_marketplace(repo_root, plugin_dirs)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid Claude marketplace {marketplace}: {exc}")
        else:
            if plugin in (None, "", "all") and not codex.json_equal(
                actual_marketplace,
                expected_marketplace,
            ):
                errors.append(
                    f"{marketplace}: generated content is not in sync with {codex.PLUGIN_METADATA}"
                )

    return errors
