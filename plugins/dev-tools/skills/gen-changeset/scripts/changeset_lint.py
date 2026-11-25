#!/usr/bin/env python3
"""Validate Changesets files against the repository workspace.

Stdlib only. Checks syntax, package names, bump values, summary quality,
empty changesets, ignored/private packages, and fixed groups. It never runs
the Changesets CLI, changes versions, or touches git history.
"""

from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

BUMP_TYPES = ("major", "minor", "patch")
GENERIC_SUMMARIES = {
    "bug fix",
    "bugfix",
    "change",
    "changes",
    "fix",
    "fix bug",
    "fix bugs",
    "fixes",
    "improvement",
    "improvements",
    "misc",
    "misc changes",
    "update",
    "updates",
    "various improvements",
    "wip",
}
MIGRATION_HINT = re.compile(
    r"(to migrate|migrat\w*|breaking change|replac\w* .{0,80} with|"
    r"use .{0,80} instead|renam\w* .{0,80} to|upgrad\w* to|"
    r"迁移|替换为|改用|升级到|改为)",
    re.IGNORECASE,
)
PLACEHOLDER_HARD = re.compile(r"\b(TODO|FIXME)\b")
PLACEHOLDER_SOFT = re.compile(r"\b(TBD|XXX)\b|<[A-Za-z][A-Za-z _-]{1,30}>")
MAINTAINER_VOICE = re.compile(r"^(this|we|i)\b", re.IGNORECASE)
FILENAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*\.md$")
EXCLUDED_DIRS = {"node_modules", ".git", "dist", "build", "vendor", "coverage", ".next", ".turbo"}


@dataclass
class Package:
    name: str
    directory: Path
    version: Optional[str]
    private: bool


@dataclass
class Issue:
    level: str
    code: str
    message: str
    path: Optional[Path] = None
    line: Optional[int] = None

    def as_dict(self, root: Path) -> dict[str, Any]:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "file": relative(self.path, root) if self.path else None,
            "line": self.line,
        }


@dataclass
class Changeset:
    path: Path
    releases: list[tuple[str, int, str]] = field(default_factory=list)
    summary: str = ""
    summary_line: int = 1
    frontmatter_parsed: bool = False
    issues: list[Issue] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return (
            self.frontmatter_parsed
            and not self.releases
            and not self.summary.strip()
        )


def relative(path: Optional[Path], root: Path) -> Optional[str]:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def run_git(root: Path, *args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False, ""
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, result.stdout.strip()


def find_root(start: Path) -> Optional[Path]:
    if not start.exists():
        return None
    ok, out = run_git(start, "rev-parse", "--show-toplevel")
    if ok and out:
        return Path(out)
    return None


def read_json(path: Path) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "must contain a JSON object"
    return data, None


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def strip_inline_comment(value: str) -> str:
    match = re.search(r"\s+#", value)
    if match:
        value = value[: match.start()]
    return value.rstrip()


def parse_list_block(lines: Iterable[str]) -> list[str]:
    values: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"^-\s*(.+)$", stripped)
        if match:
            values.append(strip_quotes(strip_inline_comment(match.group(1))))
            continue
        if not line[:1].isspace():
            break
    return values


def workspace_patterns(root: Path) -> tuple[list[str], list[str]]:
    """Return (patterns, notes) from pnpm, package.json, or lerna."""
    patterns: list[str] = []
    notes: list[str] = []
    pnpm = root / "pnpm-workspace.yaml"
    if pnpm.is_file():
        try:
            lines = pnpm.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for index, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r"^packages:\s*$", stripped):
                patterns.extend(parse_list_block(lines[index + 1 :]))
                break
            inline = re.match(r"^packages:\s*\[(.*)\]\s*$", stripped)
            if inline:
                patterns.extend(
                    strip_quotes(strip_inline_comment(item))
                    for item in inline.group(1).split(",")
                    if item.strip()
                )
                break
        if patterns:
            return patterns, notes
        notes.append("pnpm-workspace.yaml has no packages list")

    package_json = root / "package.json"
    if package_json.is_file():
        data, error = read_json(package_json)
        if data is not None:
            workspaces = data.get("workspaces")
            if isinstance(workspaces, list):
                patterns.extend(str(item) for item in workspaces)
            elif isinstance(workspaces, dict) and isinstance(workspaces.get("packages"), list):
                patterns.extend(str(item) for item in workspaces["packages"])
            if patterns:
                return patterns, notes

    lerna = root / "lerna.json"
    if lerna.is_file():
        data, error = read_json(lerna)
        if data is not None and isinstance(data.get("packages"), list):
            patterns.extend(str(item) for item in data["packages"])
    return patterns, notes


def load_package(package_json: Path) -> Optional[Package]:
    data, error = read_json(package_json)
    if data is None:
        return None
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    version = data.get("version")
    return Package(
        name=name.strip(),
        directory=package_json.parent,
        version=version if isinstance(version, str) else None,
        private=bool(data.get("private", False)),
    )


def bounded_scan(root: Path, max_depth: int = 5) -> list[Path]:
    found: list[Path] = []
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        if len(current_path.parts) - root_depth >= max_depth:
            dirs[:] = []
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        if "package.json" in files:
            found.append(current_path / "package.json")
    return found


def discover_packages(root: Path) -> tuple[dict[str, Package], list[str]]:
    patterns, notes = workspace_patterns(root)
    package_files: list[Path] = []
    negations = [p for p in patterns if p.startswith("!")]
    positives = [p for p in patterns if not p.startswith("!")]

    matched_workspace_package = False
    if positives:
        seen: set[Path] = set()
        for pattern in positives:
            clean = pattern[2:] if pattern.startswith("./") else pattern
            clean = clean.rstrip("/")
            for match in glob.glob(str(root / clean), recursive=True):
                candidate = Path(match)
                if candidate.is_file() and candidate.name == "package.json":
                    package_json = candidate
                elif candidate.is_dir() and (candidate / "package.json").is_file():
                    package_json = candidate / "package.json"
                else:
                    continue
                relative_dir = package_json.parent.relative_to(root).as_posix()
                if any(
                    fnmatch.fnmatch(relative_dir, negation[1:].rstrip("/"))
                    or fnmatch.fnmatch(relative_dir + "/", negation[1:].rstrip("/"))
                    for negation in negations
                ):
                    continue
                if package_json not in seen:
                    seen.add(package_json)
                    package_files.append(package_json)
                    if package_json.parent != root:
                        matched_workspace_package = True

    root_package = root / "package.json"
    if root_package.is_file() and root_package not in package_files:
        package_files.insert(0, root_package)

    if positives and not matched_workspace_package:
        notes.append("workspace patterns matched no packages outside the root; verify the globs")
    if not package_files:
        package_files = bounded_scan(root)
        notes.append("no package.json found from the workspace config; used a bounded scan")

    packages: dict[str, Package] = {}
    for package_json in package_files:
        package = load_package(package_json)
        if package is None:
            notes.append(f"skipped {relative(package_json, root)}: missing package name")
            continue
        packages.setdefault(package.name, package)
    if not packages:
        notes.append("no workspace packages discovered; package-name checks are skipped")
    return packages, notes


def detect_base_branch(root: Path, config: dict[str, Any]) -> Optional[str]:
    configured = config.get("baseBranch")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    ok, out = run_git(root, "symbolic-ref", "refs/remotes/origin/HEAD")
    if ok and out:
        return out.rsplit("/", 1)[-1]
    for candidate in ("main", "master"):
        if run_git(root, "rev-parse", "--verify", candidate)[0]:
            return candidate
    return None


def changeset_files(
    root: Path,
    config: dict[str, Any],
    since: Optional[str],
    all_files: bool,
) -> tuple[list[Path], Optional[str], list[Issue]]:
    changeset_dir = root / ".changeset"
    issues: list[Issue] = []
    all_paths = sorted(
        path
        for path in changeset_dir.glob("*.md")
        if path.name.lower() != "readme.md" and not path.name.startswith(".")
    )
    if all_files:
        return all_paths, detect_base_branch(root, config), issues

    base = since or detect_base_branch(root, config)
    if base is None:
        issues.append(
            Issue(
                "warning",
                "no-base",
                "No base branch found; validating all pending changesets.",
                changeset_dir,
            )
        )
        return all_paths, None, issues

    merge_base_ok, merge_base = run_git(root, "merge-base", base, "HEAD")
    comparison = merge_base if merge_base_ok and merge_base else base
    if not merge_base_ok:
        issues.append(
            Issue(
                "warning",
                "unresolved-base",
                f"Could not resolve base ref '{base}'; using it directly for the diff.",
                changeset_dir,
            )
        )

    names: set[str] = set()
    commands = [
        ("diff", "--name-only", "--diff-filter=AM", f"{comparison}..HEAD", "--", ".changeset"),
        ("diff", "--name-only", "--cached", "--", ".changeset"),
        ("diff", "--name-only", "--", ".changeset"),
        ("ls-files", "--others", "--exclude-standard", "--", ".changeset"),
    ]
    for command in commands:
        ok, out = run_git(root, *command)
        if not ok:
            continue
        for line in out.splitlines():
            if line.strip():
                names.add(line.strip())

    selected = []
    for name in sorted(names):
        path = root / name
        if path.suffix.lower() != ".md" or path.name.lower() == "readme.md":
            continue
        if not path.exists():
            continue
        selected.append(path)

    if not selected:
        issues.append(
            Issue(
                "warning",
                "no-changesets",
                f"No new changeset files found since {base}.",
                changeset_dir,
            )
        )
    return selected, base, issues


def parse_changeset(path: Path) -> Changeset:
    changeset = Changeset(path=path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        changeset.issues.append(Issue("error", "unreadable", str(exc), path, 1))
        return changeset

    if not text.strip():
        changeset.issues.append(
            Issue("error", "empty-file", "Changeset file is empty.", path, 1)
        )
        return changeset

    lines = text.splitlines()
    opening = next((index for index, line in enumerate(lines) if line.strip()), None)
    if opening is None or lines[opening].strip() != "---":
        changeset.issues.append(
            Issue(
                "error",
                "missing-frontmatter",
                "Changeset must start with a '---' frontmatter delimiter.",
                path,
                (opening or 0) + 1,
            )
        )
        return changeset

    closing = None
    for index in range(opening + 1, len(lines)):
        if lines[index].strip() == "---":
            closing = index
            break
    if closing is None:
        changeset.issues.append(
            Issue(
                "error",
                "unterminated-frontmatter",
                "Missing closing '---' frontmatter delimiter.",
                path,
                opening + 1,
            )
        )
        return changeset

    changeset.frontmatter_parsed = True
    seen_names: set[str] = set()
    in_override_block = False
    for index in range(opening + 1, closing):
        raw = lines[index]
        line_number = index + 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw:
            changeset.issues.append(
                Issue(
                    "error",
                    "tab-indent",
                    "Tabs are not valid YAML indentation; use spaces.",
                    path,
                    line_number,
                )
            )
            raw = raw.replace("\t", "  ")
        if raw[:1].isspace():
            if in_override_block:
                continue  # nested block, e.g. changelog-github '_' overrides
            raw = raw.lstrip()
        else:
            in_override_block = False
        if ":" not in raw:
            changeset.issues.append(
                Issue(
                    "error",
                    "bad-frontmatter-line",
                    f"Expected 'package: bump', got: {raw.strip()}",
                    path,
                    line_number,
                )
            )
            continue
        key, value = raw.split(":", 1)
        raw_key = key.strip()
        name = strip_quotes(key)
        if not name:
            changeset.issues.append(
                Issue(
                    "error",
                    "missing-package-name",
                    "Frontmatter entry has no package name.",
                    path,
                    line_number,
                )
            )
            continue
        if raw_key.startswith("@") and raw_key[:1] not in "\"'":
            changeset.issues.append(
                Issue(
                    "error",
                    "unquoted-scoped-name",
                    f'Scoped package "{name}" must be quoted in YAML.',
                    path,
                    line_number,
                )
            )
        if name == "_":
            in_override_block = True
            continue
        raw_bump = strip_quotes(strip_inline_comment(value))
        bump = raw_bump.lower()
        if not bump:
            changeset.issues.append(
                Issue(
                    "error",
                    "missing-bump",
                    f'Missing bump type for "{name}".',
                    path,
                    line_number,
                )
            )
            continue
        if raw_bump != bump and bump in BUMP_TYPES:
            changeset.issues.append(
                Issue(
                    "error",
                    "bump-case",
                    f'Bump "{raw_bump}" must be lowercase: major, minor, or patch.',
                    path,
                    line_number,
                )
            )
            seen_names.add(name)
            changeset.releases.append((name, line_number, bump))
            continue
        if bump not in BUMP_TYPES:
            changeset.issues.append(
                Issue(
                    "error",
                    "invalid-bump",
                    f'Invalid bump "{bump}" for "{name}"; expected major, minor, or patch.',
                    path,
                    line_number,
                )
            )
            continue
        if name in seen_names:
            changeset.issues.append(
                Issue(
                    "warning",
                    "duplicate-package",
                    f'Package "{name}" appears more than once; the last bump wins.',
                    path,
                    line_number,
                )
            )
        seen_names.add(name)
        changeset.releases.append((name, line_number, bump))

    changeset.summary = "\n".join(lines[closing + 1 :]).strip()
    changeset.summary_line = closing + 2
    return changeset


def validate_summary(changeset: Changeset, bump_types: set[str]) -> None:
    summary = changeset.summary
    path = changeset.path
    line = changeset.summary_line
    if not changeset.releases:
        if summary:
            changeset.issues.append(
                Issue(
                    "warning",
                    "no-packages",
                    "Summary has no package entries; this changeset will not release anything.",
                    path,
                    line,
                )
            )
        return
    if not summary:
        changeset.issues.append(
            Issue(
                "error",
                "missing-summary",
                "Non-empty changeset is missing a summary.",
                path,
                line,
            )
        )
        return
    if PLACEHOLDER_HARD.search(summary):
        changeset.issues.append(
            Issue(
                "error",
                "placeholder",
                "Summary contains TODO/FIXME; finish the text before delivery.",
                path,
                line,
            )
        )
    elif PLACEHOLDER_SOFT.search(summary):
        changeset.issues.append(
            Issue(
                "warning",
                "placeholder",
                "Summary may contain an unresolved placeholder (TBD/XXX/<...>).",
                path,
                line,
            )
        )

    first_line = next((item.strip() for item in summary.splitlines() if item.strip()), "")
    normalized = re.sub(r"[.!]+$", "", first_line.lower()).strip()
    word_count = len(re.findall(r"[\w'-]+", first_line))
    if normalized in GENERIC_SUMMARIES or (word_count <= 2 and "`" not in first_line):
        changeset.issues.append(
            Issue(
                "warning",
                "generic-summary",
                "Summary is too generic; name the public symbol or behavior.",
                path,
                line,
            )
        )
    if MAINTAINER_VOICE.search(first_line):
        changeset.issues.append(
            Issue(
                "warning",
                "maintainer-voice",
                "Summary addresses the maintainer; lead with the consumer-visible effect.",
                path,
                line,
            )
        )
    if len(summary) < 15:
        changeset.issues.append(
            Issue("warning", "short-summary", "Summary is very short.", path, line)
        )
    if len(summary) > 6000:
        changeset.issues.append(
            Issue(
                "warning",
                "long-summary",
                "Summary is very long; move detail to docs and keep the changelog scannable.",
                path,
                line,
            )
        )
    if (
        "major" in bump_types
        and "```" not in summary
        and not MIGRATION_HINT.search(summary)
    ):
        changeset.issues.append(
            Issue(
                "warning",
                "major-without-migration",
                "Major bump without migration/upgrade guidance.",
                path,
                line,
            )
        )


def validate_packages(
    changeset: Changeset,
    packages: dict[str, Package],
    config: dict[str, Any],
) -> None:
    if not packages:
        return
    names = [name for name, _, _ in changeset.releases]
    ignore_config = config.get("ignore")
    ignore = (
        {str(item) for item in ignore_config if isinstance(item, str)}
        if isinstance(ignore_config, list)
        else set()
    )
    private_version = False
    private_config = config.get("privatePackages")
    if isinstance(private_config, dict):
        private_version = bool(private_config.get("version", False))

    for name, line, _ in changeset.releases:
        if name not in packages:
            changeset.issues.append(
                Issue(
                    "error",
                    "unknown-package",
                    f'Package "{name}" is not in the workspace.',
                    changeset.path,
                    line,
                )
            )
            continue
        package = packages[name]
        if package.private and not private_version and name not in ignore:
            changeset.issues.append(
                Issue(
                    "warning",
                    "private-unversioned",
                    f'"{name}" is private and privatePackages.version is false; it will not be released.',
                    changeset.path,
                    line,
                )
            )

    released = [name for name in names if name not in ignore]
    ignored_here = [name for name in names if name in ignore]
    if ignored_here and released:
        changeset.issues.append(
            Issue(
                "error",
                "mixed-ignore",
                "Changeset mixes ignored packages ("
                + ", ".join(ignored_here)
                + ") with released packages; `changeset version` may fail.",
                changeset.path,
                changeset.summary_line,
            )
        )
    elif ignored_here:
        changeset.issues.append(
            Issue(
                "warning",
                "all-ignored",
                "All packages are in config.ignore; nothing will be released.",
                changeset.path,
                changeset.summary_line,
            )
        )

    fixed = config.get("fixed")
    if isinstance(fixed, list) and released:
        for group in fixed:
            if not isinstance(group, list):
                continue
            patterns = [str(item) for item in group]
            members = [
                name
                for name in names
                if any(fnmatch.fnmatch(name, pattern) or name == pattern for pattern in patterns)
            ]
            bumps = {bump for name, _, bump in changeset.releases if name in members}
            if len(members) > 1 and len(bumps) > 1:
                changeset.issues.append(
                    Issue(
                        "warning",
                        "fixed-mixed-bump",
                        "Fixed group members use different bumps; the highest bump applies to all.",
                        changeset.path,
                        changeset.summary_line,
                    )
                )


def validate_filename(changeset: Changeset) -> None:
    if not FILENAME_PATTERN.match(changeset.path.name):
        changeset.issues.append(
            Issue(
                "warning",
                "filename",
                "Prefer a lowercase kebab-case filename (e.g. add-csv-export.md).",
                changeset.path,
                1,
            )
        )


def suggested_command(root: Path, base: Optional[str]) -> str:
    ref = base or "<base>"
    if (root / "pnpm-lock.yaml").is_file():
        return f"pnpm changeset status --since {ref}"
    if (root / "yarn.lock").is_file():
        return f"yarn changeset status --since {ref}"
    if (root / "bun.lockb").is_file() or (root / "bun.lock").is_file():
        return f"bunx @changesets/cli status --since {ref}"
    return f"npx --no-install @changesets/cli status --since {ref}"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Changesets files against the workspace.",
        epilog=(
            "Exit codes: 0 clean, 1 errors (or warnings with --strict), "
            "2 setup error (no repository or .changeset/config.json)."
        ),
    )
    parser.add_argument("--repo", default=".", help="Repository path (default: cwd).")
    parser.add_argument("--since", help="Base ref for new changesets.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate every pending changeset instead of only new/changed ones.",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Exit 1 when warnings remain."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    start = Path(args.repo).expanduser()
    root = find_root(start) or (start.resolve() if start.is_dir() else None)
    if root is None:
        print(f"error: repository path not found: {start}", file=sys.stderr)
        return 2

    config_path = root / ".changeset" / "config.json"
    if not config_path.is_file():
        print(
            f"error: {relative(config_path, root)} not found; this is not a Changesets repository.",
            file=sys.stderr,
        )
        return 2

    config, config_error = read_json(config_path)
    setup_issues: list[Issue] = []
    if config is None:
        setup_issues.append(
            Issue("error", "invalid-config", f"Invalid config.json: {config_error}", config_path)
        )
        config = {}

    packages, package_notes = discover_packages(root)
    for note in package_notes:
        setup_issues.append(Issue("warning", "workspace", note, root / "package.json"))

    files, base, file_issues = changeset_files(root, config, args.since, args.all)
    setup_issues.extend(file_issues)

    changesets: list[Changeset] = []
    for path in files:
        changeset = parse_changeset(path)
        validate_filename(changeset)
        validate_packages(changeset, packages, config)
        validate_summary(changeset, {bump for _, _, bump in changeset.releases})
        changesets.append(changeset)

    issues = setup_issues + [issue for item in changesets for issue in item.issues]
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    exit_code = 1 if errors or (args.strict and warnings) else 0

    if args.json:
        payload = {
            "repo": str(root),
            "mode": "changesets",
            "base": base,
            "packages": sorted(packages),
            "changesets": [
                {
                    "file": relative(item.path, root),
                    "empty": item.is_empty,
                    "releases": [
                        {"package": name, "line": line, "bump": bump}
                        for name, line, bump in item.releases
                    ],
                    "summary": item.summary,
                    "issues": [issue.as_dict(root) for issue in item.issues],
                }
                for item in changesets
            ],
            "issues": [issue.as_dict(root) for issue in issues],
            "summary": {
                "changesets": len(changesets),
                "errors": len(errors),
                "warnings": len(warnings),
            },
            "suggested_command": suggested_command(root, base),
            "exit_code": exit_code,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return exit_code

    if not changesets and not setup_issues:
        print("No pending changesets found.")
    for issue in setup_issues:
        location = f"line {issue.line}:" if issue.line else ""
        print(
            f"{relative(issue.path, root) or 'workspace'}: "
            f"{issue.level} [{issue.code}] {location} {issue.message}"
        )
    for item in changesets:
        print(relative(item.path, root))
        if item.is_empty:
            print("  info   [empty] empty changeset (releases nothing)")
        if not item.issues:
            print("  ok")
            continue
        for issue in sorted(item.issues, key=lambda value: (value.line or 0, value.code)):
            location = f"line {issue.line}:" if issue.line else ""
            print(f"  {issue.level:<7}[{issue.code}] {location} {issue.message}")
    print()
    print(
        f"{len(changesets)} changeset(s), {len(errors)} error(s), {len(warnings)} warning(s)"
    )
    if packages:
        print(f"packages: {len(packages)} discovered")
    print(f"next check: {suggested_command(root, base)}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
