"""Codex plugin generation helpers."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import hook_intents


PLUGIN_MANIFEST = ".codex-plugin/plugin.json"
MARKETPLACE_PATH = ".agents/plugins/marketplace.json"
DEFAULT_MARKETPLACE_NAME = "poseidon"
PACKAGE_ROOT = ".codex/generated/plugins"
PLUGIN_METADATA = "plugins/plugin-metadata.json"


def discover_plugin_dirs(repo_root: Path) -> list[Path]:
    metadata = read_metadata(repo_root)
    plugins = metadata["plugins"]
    return sorted(
        repo_root / "plugins" / name
        for name in plugins
        if (repo_root / "plugins" / name).is_dir()
    )


def select_plugin_dirs(repo_root: Path, plugin: str | None = None) -> list[Path]:
    plugin_dirs = discover_plugin_dirs(repo_root)
    if plugin in (None, "", "all"):
        return plugin_dirs

    selected = [path for path in plugin_dirs if path.name == plugin]
    if not selected:
        known = ", ".join(path.name for path in plugin_dirs) or "(none)"
        raise ValueError(f"Unknown plugin '{plugin}'. Known plugins: {known}")
    return selected


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def package_root(repo_root: Path) -> Path:
    return repo_root / PACKAGE_ROOT


def package_plugin_path(repo_root: Path, plugin_name: str) -> Path:
    return package_root(repo_root) / plugin_name


def package_source_path(plugin_name: str) -> str:
    return f"./{PACKAGE_ROOT}/{plugin_name}"


def metadata_path(repo_root: Path) -> Path:
    return repo_root / PLUGIN_METADATA


def read_metadata(repo_root: Path) -> dict[str, Any]:
    metadata = read_json(metadata_path(repo_root))
    plugins = metadata.get("plugins")
    if not isinstance(plugins, dict):
        raise ValueError(f"{metadata_path(repo_root)} must contain a plugins object")
    return metadata


def plugin_metadata(plugin_dir: Path) -> dict[str, Any]:
    repo_root = plugin_dir.parents[1]
    metadata = read_metadata(repo_root)
    plugins = metadata["plugins"]
    plugin = plugins.get(plugin_dir.name)
    if not isinstance(plugin, dict):
        raise ValueError(f"{metadata_path(repo_root)} missing metadata for plugin '{plugin_dir.name}'")
    return plugin


def marketplace_metadata(repo_root: Path) -> dict[str, Any]:
    metadata = read_metadata(repo_root)
    marketplace = metadata.get("marketplace")
    if not isinstance(marketplace, dict):
        return {
            "name": DEFAULT_MARKETPLACE_NAME,
            "displayName": "Poseidon",
        }
    return marketplace


def marketplace_name(repo_root: Path) -> str:
    return str(marketplace_metadata(repo_root).get("name") or DEFAULT_MARKETPLACE_NAME)


def cache_plugin_root(plugin_name: str, version: str, repo_root: Path | None = None) -> str:
    marketplace = marketplace_name(repo_root) if repo_root is not None else DEFAULT_MARKETPLACE_NAME
    return f"$HOME/.codex/plugins/cache/{marketplace}/{plugin_name}/{version}"


def cache_plugin_root_windows(plugin_name: str, version: str, repo_root: Path | None = None) -> str:
    marketplace = marketplace_name(repo_root) if repo_root is not None else DEFAULT_MARKETPLACE_NAME
    return rf"%USERPROFILE%\.codex\plugins\cache\{marketplace}\{plugin_name}\{version}"


def hook_intent_context(plugin_dir: Path) -> dict[str, str]:
    manifest = generate_plugin_manifest(plugin_dir)
    plugin_name = str(manifest["name"])
    version = str(manifest["version"])
    repo_root = plugin_dir.parents[1]
    return {
        "PLUGIN_NAME": plugin_name,
        "PLUGIN_VERSION": version,
        "MARKETPLACE_NAME": marketplace_name(repo_root),
        "CODEX_CACHE_PLUGIN_ROOT": cache_plugin_root(plugin_name, version, repo_root),
        "CODEX_CACHE_PLUGIN_ROOT_WINDOWS": cache_plugin_root_windows(plugin_name, version, repo_root),
        "CLAUDE_PLUGIN_ROOT": "${CLAUDE_PLUGIN_ROOT}",
    }


def render_codex_hooks(plugin_dir: Path) -> dict[str, Any] | None:
    rendered_intents = hook_intents.render_platform_hooks(
        plugin_dir,
        "codex",
        hook_intent_context(plugin_dir),
    )
    if rendered_intents is not None:
        return rendered_intents

    template_path = plugin_dir / "hooks" / "codex" / "hooks.json"
    if not template_path.exists():
        return None

    manifest = generate_plugin_manifest(plugin_dir)
    plugin_name = str(manifest["name"])
    version = str(manifest["version"])
    repo_root = plugin_dir.parents[1]
    replacements = {
        "{{PLUGIN_NAME}}": plugin_name,
        "{{PLUGIN_VERSION}}": version,
        "{{MARKETPLACE_NAME}}": marketplace_name(repo_root),
        "{{CODEX_CACHE_PLUGIN_ROOT}}": cache_plugin_root(plugin_name, version, repo_root),
        "{{CODEX_CACHE_PLUGIN_ROOT_WINDOWS}}": cache_plugin_root_windows(plugin_name, version, repo_root),
    }

    rendered = template_path.read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, json.dumps(value)[1:-1])

    return json.loads(rendered)


def render_codex_hooks_template(plugin_dir: Path, target: Path) -> None:
    hooks = render_codex_hooks(plugin_dir)
    if hooks is None:
        return
    write_json(target / "hooks" / "hooks.json", hooks)


def copy_codex_package(repo_root: Path, plugin_dir: Path) -> Path:
    target = package_plugin_path(repo_root, plugin_dir.name)
    if target.exists():
        shutil.rmtree(target)

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {".claude-plugin", "__pycache__"}
        directory_path = Path(directory)
        if directory_path == plugin_dir / "hooks":
            if "hooks.json" in names:
                ignored.add("hooks.json")
            if "claude" in names:
                ignored.add("claude")
        return ignored.intersection(names)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(plugin_dir, target, ignore=ignore)

    write_json(target / PLUGIN_MANIFEST, generate_plugin_manifest(plugin_dir))
    render_codex_hooks_template(plugin_dir, target)
    return target


def display_name(plugin_name: str) -> str:
    return " ".join(part.capitalize() for part in plugin_name.split("-"))


def short_description(description: str) -> str:
    normalized = re.sub(r"\s+", " ", description).strip()
    if len(normalized) <= 160:
        return normalized
    return normalized[:157].rstrip() + "..."


def developer_name(author: Any) -> str:
    if isinstance(author, dict) and author.get("name"):
        return str(author["name"])
    if isinstance(author, str) and author:
        return author
    return "Poseidon"


def generate_plugin_manifest(plugin_dir: Path) -> dict[str, Any]:
    metadata = plugin_metadata(plugin_dir)
    name = plugin_dir.name
    description = str(metadata.get("description") or "")
    author = metadata.get("author") or {"name": "Poseidon"}

    manifest: dict[str, Any] = {
        "name": name,
        "version": str(metadata.get("version") or "0.1.0"),
        "description": description,
        "author": author,
        "license": str(metadata.get("license") or "MIT"),
        "keywords": list(metadata.get("keywords") or []),
        "skills": "./skills/",
        "interface": {
            "displayName": display_name(name),
            "shortDescription": short_description(description),
            "longDescription": description,
            "developerName": developer_name(author),
            "category": str(metadata.get("category") or "Productivity"),
            "capabilities": ["Skills"],
        },
    }

    return manifest


def plugin_manifest_path(plugin_dir: Path) -> Path:
    return plugin_dir / PLUGIN_MANIFEST


def generate_marketplace_entry(plugin_dir: Path) -> dict[str, Any]:
    manifest = generate_plugin_manifest(plugin_dir)
    name = manifest["name"]
    return {
        "name": name,
        "source": {
            "source": "local",
            "path": package_source_path(name),
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": manifest["interface"]["category"],
    }


def generate_marketplace(repo_root: Path, plugin_dirs: list[Path] | None = None) -> dict[str, Any]:
    if plugin_dirs is None:
        plugin_dirs = discover_plugin_dirs(repo_root)
    entries = [generate_marketplace_entry(plugin_dir) for plugin_dir in plugin_dirs]
    marketplace = marketplace_metadata(repo_root)
    return {
        "name": str(marketplace.get("name") or DEFAULT_MARKETPLACE_NAME),
        "interface": {
            "displayName": str(marketplace.get("displayName") or "Poseidon"),
        },
        "plugins": entries,
    }


def generate_marketplace_update(repo_root: Path, selected_plugin_dirs: list[Path]) -> dict[str, Any]:
    path = marketplace_path(repo_root)
    if path.exists():
        marketplace = read_json(path)
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list):
            plugins = []
    else:
        marketplace = {
            "name": marketplace_name(repo_root),
            "interface": {
                "displayName": str(marketplace_metadata(repo_root).get("displayName") or "Poseidon"),
            },
            "plugins": [],
        }
        plugins = []

    selected_entries = {
        entry["name"]: entry
        for entry in (generate_marketplace_entry(plugin_dir) for plugin_dir in selected_plugin_dirs)
    }
    updated_entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in plugins:
        if isinstance(entry, dict) and entry.get("name") in selected_entries:
            name = str(entry["name"])
            updated_entries.append(selected_entries[name])
            seen.add(name)
        elif isinstance(entry, dict):
            updated_entries.append(entry)

    for name, entry in selected_entries.items():
        if name not in seen:
            updated_entries.append(entry)

    marketplace["plugins"] = updated_entries
    return marketplace


def marketplace_path(repo_root: Path) -> Path:
    return repo_root / MARKETPLACE_PATH


def json_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return json.dumps(left, ensure_ascii=False, sort_keys=True) == json.dumps(
        right,
        ensure_ascii=False,
        sort_keys=True,
    )
