"""Cursor skill install helpers.

Cursor discovers Agent Skills from `.cursor/skills/<name>/SKILL.md` or
`.agents/skills/<name>/SKILL.md` (project), and the corresponding user-level
directories. Poseidon uses the shared `~/.agents/skills` location globally.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from adapters import codex


PROJECT_SKILL_PATH = ".cursor/skills"
USER_SKILL_PATH = Path.home() / ".cursor" / "skills"
AGENTS_USER_SKILL_PATH = Path.home() / ".agents" / "skills"


def discover_plugin_dirs(repo_root: Path) -> list[Path]:
    return codex.discover_plugin_dirs(repo_root)


def select_plugin_dirs(repo_root: Path, plugin: str | None = None) -> list[Path]:
    return codex.select_plugin_dirs(repo_root, plugin)


def parse_frontmatter_name(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() == "name":
            return value.strip().strip('"').strip("'")
    return None


def skill_name(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        name = parse_frontmatter_name(skill_md)
        if name:
            return name
    return skill_dir.name


def discover_skill_dirs(plugin_dirs: list[Path]) -> list[Path]:
    skill_dirs: list[Path] = []
    for plugin_dir in plugin_dirs:
        skills_root = plugin_dir / "skills"
        if not skills_root.is_dir():
            continue
        for skill_dir in sorted(skills_root.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").is_file():
                skill_dirs.append(skill_dir)
    return skill_dirs


def skill_install_root(repo_root: Path, scope: str, mode: str = "agent") -> Path:
    if scope == "user":
        return AGENTS_USER_SKILL_PATH if mode == "agents" else USER_SKILL_PATH
    if scope == "repo":
        return repo_root / (".agents/skills" if mode == "agents" else PROJECT_SKILL_PATH)
    raise ValueError(f"Unsupported Cursor scope: {scope}")


def skill_target_path(repo_root: Path, scope: str, skill_dir: Path, mode: str = "agent") -> Path:
    return skill_install_root(repo_root, scope, mode) / skill_name(skill_dir)


def copy_skill(skill_dir: Path, target: Path) -> Path:
    if target.exists():
        shutil.rmtree(target)

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {"__pycache__"}.intersection(names)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_dir, target, ignore=ignore)
    return target


def install_skills(
    repo_root: Path,
    scope: str,
    plugin: str | None = None,
) -> list[Path]:
    plugin_dirs = select_plugin_dirs(repo_root, plugin)
    installed: list[Path] = []
    for skill_dir in discover_skill_dirs(plugin_dirs):
        target = skill_target_path(repo_root, scope, skill_dir)
        installed.append(copy_skill(skill_dir, target))
    return installed


def validate(repo_root: Path, scope: str = "repo", plugin: str | None = None) -> list[str]:
    """Validate installed Cursor skills when the install root exists."""
    errors: list[str] = []
    install_root = skill_install_root(repo_root, scope)
    if not install_root.exists():
        return errors

    plugin_dirs = select_plugin_dirs(repo_root, plugin)
    expected = {
        skill_name(skill_dir): skill_dir
        for skill_dir in discover_skill_dirs(plugin_dirs)
    }

    for name, skill_dir in sorted(expected.items()):
        target = install_root / name
        skill_md = target / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"Missing installed Cursor skill: {skill_md}")
            continue
        installed_name = parse_frontmatter_name(skill_md)
        if installed_name != name:
            errors.append(
                f"{skill_md}: installed skill name '{installed_name}' "
                f"does not match target folder '{name}'"
            )
        source_md = skill_dir / "SKILL.md"
        if skill_md.read_text(encoding="utf-8") != source_md.read_text(encoding="utf-8"):
            errors.append(
                f"{skill_md}: installed content is not in sync with {source_md}"
            )

    return errors
