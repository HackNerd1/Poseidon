"""Load the repository platform matrix without external YAML dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def load_platforms(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Parse the small YAML subset used by scripts/platforms.yaml."""
    path = repo_root / "scripts" / "platforms.yaml"
    platforms: dict[str, dict[str, Any]] = {}
    current: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.strip() == "platforms:":
            continue

        if raw_line.startswith("  ") and not raw_line.startswith("    ") and raw_line.rstrip().endswith(":"):
            current = raw_line.strip()[:-1]
            platforms[current] = {}
            continue

        if current and raw_line.startswith("    ") and ":" in raw_line:
            key, value = raw_line.strip().split(":", 1)
            platforms[current][key] = _parse_scalar(value)

    return platforms


def implemented_platforms(repo_root: Path) -> tuple[str, ...]:
    platforms = load_platforms(repo_root)
    return tuple(name for name, config in platforms.items() if config.get("implemented", False))
