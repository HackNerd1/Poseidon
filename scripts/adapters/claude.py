"""Claude plugin validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
MARKETPLACE_PATH = ".claude-plugin/marketplace.json"


def discover_plugin_dirs(repo_root: Path) -> list[Path]:
    plugins_root = repo_root / "plugins"
    if not plugins_root.exists():
        return []
    return sorted(path for path in plugins_root.iterdir() if path.is_dir())


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def validate(repo_root: Path, plugin: str | None = None) -> list[str]:
    errors: list[str] = []
    plugin_dirs = discover_plugin_dirs(repo_root)
    if plugin not in (None, "", "all"):
        plugin_dirs = [path for path in plugin_dirs if path.name == plugin]
        if not plugin_dirs:
            errors.append(f"Unknown plugin '{plugin}'")
            return errors

    for plugin_dir in plugin_dirs:
        manifest = plugin_dir / PLUGIN_MANIFEST
        if not manifest.exists():
            errors.append(f"Missing Claude manifest: {manifest}")
            continue
        try:
            read_json(manifest)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid Claude manifest {manifest}: {exc}")

    marketplace = repo_root / MARKETPLACE_PATH
    if marketplace.exists():
        try:
            read_json(marketplace)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid Claude marketplace {marketplace}: {exc}")

    return errors
