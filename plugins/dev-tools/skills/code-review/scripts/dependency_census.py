#!/usr/bin/env python3
"""Dependency census for code review.

Usage:
    python3 scripts/dependency_census.py path/to/module.ts
    python3 scripts/dependency_census.py path/to/module.ts --format json
    python3 scripts/dependency_census.py path/to/module.ts --repo /abs/repo/path

The script is intentionally heuristic. It helps reviewers produce a concrete
fan-in / fan-out summary, plus likely caller and test coverage candidates.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


CODE_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".py",
    ".go",
    ".java",
    ".kt",
    ".rs",
}

TEST_HINTS = (
    ".test.",
    ".spec.",
    "__tests__",
    "tests/",
    "test/",
)


@dataclass
class CensusResult:
    module: str
    repo_root: str
    fan_in_status: str
    fan_out_status: str
    inbound_dependents: list[str]
    outbound_dependencies: list[str]
    test_candidates: list[str]
    blind_spots: list[str]


IMPORT_PATTERNS = [
    re.compile(r"""import\s+(?:type\s+)?(?:.+?\s+from\s+)?["']([^"']+)["']"""),
    re.compile(r"""export\s+.+?\s+from\s+["']([^"']+)["']"""),
    re.compile(r"""require\(\s*["']([^"']+)["']\s*\)"""),
    re.compile(r"""from\s+([A-Za-z0-9_./-]+)\s+import\s+"""),
    re.compile(r"""import\s+([A-Za-z0-9_.,\s]+)$"""),
]


def run_rg(repo_root: Path, pattern: str) -> list[str]:
    command = [
        "rg",
        "-l",
        "--hidden",
        "--glob",
        "!.git",
        "--glob",
        "!node_modules",
        "--glob",
        "!dist",
        "--glob",
        "!build",
        pattern,
        str(repo_root),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "rg failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def normalize_module_path(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def build_import_candidates(module_rel: str) -> set[str]:
    module_path = Path(module_rel)
    no_suffix = module_path.with_suffix("").as_posix()
    stem = module_path.stem
    parent = module_path.parent.as_posix()

    candidates = {
        module_rel,
        no_suffix,
        f"./{stem}",
        f"../{stem}",
        stem,
    }
    if parent and parent != ".":
        candidates.add(f"{parent}/{stem}")
        candidates.add(f"{parent}/{module_path.name}")

    if module_path.name.startswith("index.") and parent and parent != ".":
        candidates.add(parent)
        candidates.add(f"./{Path(parent).name}")
        candidates.add(f"../{Path(parent).name}")

    return {candidate for candidate in candidates if candidate}


def looks_like_test(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/")
    return any(hint in normalized for hint in TEST_HINTS)


def discover_inbound_dependents(module_path: Path, repo_root: Path) -> list[str]:
    module_rel = normalize_module_path(module_path, repo_root)
    candidates = build_import_candidates(module_rel)
    hits: set[str] = set()
    for candidate in sorted(candidates):
        escaped = re.escape(candidate)
        for file_path in run_rg(repo_root, escaped):
            rel = Path(file_path).resolve().relative_to(repo_root.resolve()).as_posix()
            if rel == module_rel:
                continue
            hits.add(rel)
    return sorted(hit for hit in hits if Path(hit).suffix in CODE_EXTENSIONS)


def parse_outbound_dependencies(module_path: Path) -> list[str]:
    text = read_text(module_path)
    dependencies: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "*")):
            continue
        for pattern in IMPORT_PATTERNS:
            match = pattern.search(stripped)
            if not match:
                continue
            value = match.group(1).strip()
            if "," in value and " " in value and not value.startswith("."):
                parts = [part.strip() for part in value.split(",")]
                dependencies.update(part for part in parts if part)
            else:
                dependencies.add(value)
    return sorted(dependencies)


def discover_test_candidates(
    module_path: Path,
    repo_root: Path,
    inbound_dependents: list[str],
) -> list[str]:
    targets = {
        normalize_module_path(module_path, repo_root),
        module_path.stem,
    }
    targets.update(Path(path).stem for path in inbound_dependents[:20])
    hits: set[str] = set()
    for target in sorted(targets):
        escaped = re.escape(target)
        for file_path in run_rg(repo_root, escaped):
            rel = Path(file_path).resolve().relative_to(repo_root.resolve()).as_posix()
            if looks_like_test(rel):
                hits.add(rel)
    return sorted(hits)


def infer_blind_spots(
    inbound_dependents: list[str],
    test_candidates: list[str],
) -> list[str]:
    blind_spots: list[str] = []
    non_test_dependents = [dep for dep in inbound_dependents if not looks_like_test(dep)]
    if non_test_dependents and not test_candidates:
        blind_spots.append("No candidate tests found for the changed module or its dependents.")
    if len(non_test_dependents) > 8:
        blind_spots.append(
            "High inbound dependent count; manual inspection should prioritize entry points and shared flows."
        )
    return blind_spots


def render_text(result: CensusResult) -> str:
    def render_items(items: list[str], empty_label: str = "<none found>") -> list[str]:
        if not items:
            return [f"- {empty_label}"]
        return [f"- {item}" for item in items]

    lines = [
        f"Module: {result.module}",
        f"Repo: {result.repo_root}",
        f"Fan-in: {result.fan_in_status} ({len(result.inbound_dependents)} dependents)",
        f"Fan-out: {result.fan_out_status} ({len(result.outbound_dependencies)} dependencies)",
        "",
        "Inbound dependents:",
    ]
    lines.extend(render_items(result.inbound_dependents))
    lines.append("")
    lines.append("Outbound dependencies:")
    lines.extend(render_items(result.outbound_dependencies))
    lines.append("")
    lines.append("Test candidates:")
    lines.extend(render_items(result.test_candidates))
    lines.append("")
    lines.append("Blind spots:")
    lines.extend(render_items(result.blind_spots, empty_label="<none noted>"))
    return "\n".join(lines)


def render_markdown(result: CensusResult) -> str:
    lines = [
        "## Architecture Coverage",
        f"- Module: `{result.module}`",
        f"- Fan-in: {result.fan_in_status}, {len(result.inbound_dependents)} dependents found",
        f"- Fan-out: {result.fan_out_status}, {len(result.outbound_dependencies)} dependencies found",
        f"- Inbound dependents inspected: `{'`, `'.join(result.inbound_dependents[:8])}`"
        if result.inbound_dependents
        else "- Inbound dependents inspected: `<none found>`",
        f"- Outbound dependencies inspected: `{'`, `'.join(result.outbound_dependencies[:8])}`"
        if result.outbound_dependencies
        else "- Outbound dependencies inspected: `<none found>`",
        f"- Tests inspected: `{'`, `'.join(result.test_candidates[:8])}`"
        if result.test_candidates
        else "- Tests inspected: `<none found>`",
        f"- Blind spots: {'; '.join(result.blind_spots)}" if result.blind_spots else "- Blind spots: `<none noted>`",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--format", choices=("text", "json", "md"), default="text")
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    module_path = Path(args.module)
    if not module_path.is_absolute():
        module_path = (repo_root / module_path).resolve()

    if not module_path.exists():
        print(f"Module not found: {module_path}", file=sys.stderr)
        return 1

    inbound_dependents = discover_inbound_dependents(module_path, repo_root)
    outbound_dependencies = parse_outbound_dependencies(module_path)
    test_candidates = discover_test_candidates(module_path, repo_root, inbound_dependents)
    blind_spots = infer_blind_spots(inbound_dependents, test_candidates)

    result = CensusResult(
        module=normalize_module_path(module_path, repo_root),
        repo_root=repo_root.as_posix(),
        fan_in_status="approximate",
        fan_out_status="exact for direct imports; approximate for indirect runtime edges",
        inbound_dependents=inbound_dependents,
        outbound_dependencies=outbound_dependencies,
        test_candidates=test_candidates,
        blind_spots=blind_spots,
    )

    if args.format == "json":
        print(json.dumps(asdict(result), indent=2))
    elif args.format == "md":
        print(render_markdown(result))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
