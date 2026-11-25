#!/usr/bin/env python3
"""Deterministic README audit for the gen-readme skill.

Usage:
    python3 scripts/readme_audit.py README.md
    python3 scripts/readme_audit.py README.md --style cli --repo .
    python3 scripts/readme_audit.py packages/*/README.md --style library --repo .
    python3 scripts/readme_audit.py README.md --format json
    python3 scripts/readme_audit.py README.md --strict

Multiple paths use the same style. Run separate commands for a monorepo root
(monorepo style) and its packages (library/cli/app style).

The audit checks structure, local links/anchors, placeholders, and
style-specific section coverage. It never executes commands and never
modifies files. Warnings are expected on early drafts; errors block delivery.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

STYLES = ("generic", "library", "cli", "app", "monorepo", "internal-service")
MAX_GITHUB_BYTES = 500 * 1024
MAX_IMAGE_BYTES = 1024 * 1024

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
INLINE_LINK_RE = re.compile(
    r"(?<!\!)\[([^\]]*)\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\s*\)"
)
IMAGE_RE = re.compile(
    r"!\[([^\]]*)\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\s*\)"
)
HTML_IMG_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)
HTML_HREF_RE = re.compile(r"<a\b[^>]*\bhref=[\"']#([^\"']+)[\"']", re.IGNORECASE)
REF_DEF_RE = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*(\S+)")
ANCHOR_LINK_RE = re.compile(r"\]\(\s*#([^)\s]+)\s*\)|href=[\"']#([^\"']+)[\"']")
BADGE_RE = re.compile(
    r"\[!\[([^\]]*)\]\(\s*(<[^>]*>|[^)\s]+)[^)]*\)\]\(\s*(<[^>]*>|[^)\s]+)"
)

SKIP_SCHEMES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "data:",
    "javascript:",
    "ftp://",
    "//",
)

KNOWN_HTML_TAGS = {
    "a", "abbr", "article", "aside", "b", "blockquote", "body", "br", "button",
    "canvas", "code", "dd", "del", "details", "div", "dl", "dt", "em", "figcaption",
    "figure", "footer", "form", "g", "h1", "h2", "h3", "h4", "h5", "h6", "head",
    "header", "hr", "html", "i", "iframe", "img", "input", "kbd", "label", "li",
    "link", "main", "meta", "nav", "ol", "option", "p", "path", "picture", "pre",
    "s", "samp", "script", "section", "select", "source", "span", "strong", "style",
    "sub", "summary", "sup", "svg", "table", "tbody", "td", "template", "textarea",
    "th", "thead", "title", "tr", "u", "ul", "use", "video",
}

PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|FIXME|REPLACE_ME|YOUR_[A-Z_]+|your-org|your-project|lorem ipsum)\b",
    re.IGNORECASE,
)
ANGLE_PLACEHOLDER_RE = re.compile(r"<([A-Za-z][A-Za-z0-9 _.\-/]{0,60})>")

SECTION_ALIASES = {
    "title": (),
    "overview": ("overview", "purpose", "summary", "概述", "简介"),
    "install": (
        "install", "installation", "getting started", "quick start", "quickstart",
        "setup", "set up", "local development", "developing locally",
        "安装", "快速开始", "快速上手", "本地开发",
    ),
    "usage": (
        "usage", "how to use", "examples", "example", "使用", "用法", "示例",
    ),
    "license": ("license", "licence", "许可证", "许可"),
    "contributing": ("contributing", "development", "contributor", "贡献", "开发"),
    "config": (
        "configuration", "config", "environment variables", "settings", "options",
        "配置", "环境变量", "参数",
    ),
    "architecture": ("architecture", "design", "system design", "架构", "设计"),
    "operations": (
        "operations", "runbook", "monitoring", "deployment", "deploy", "运维",
        "部署", "监控", "值班",
    ),
    "ownership": (
        "owner", "ownership", "maintainer", "team", "contact", "support",
        "维护", "团队", "联系", "支持", "归属", "负责人",
    ),
    "structure": (
        "packages", "structure", "repository structure", "workspace", "项目结构", "包",
    ),
}

STYLE_SECTIONS = {
    "generic": ("install", "usage", "license"),
    "library": ("install", "usage", "license"),
    "cli": ("install", "usage", "license"),
    "app": ("install", "config", "usage"),
    "monorepo": ("structure", "install", "contributing", "license"),
    "internal-service": (
        "overview", "install", "config", "architecture", "operations", "ownership",
    ),
}

COMMAND_STYLES = {"library", "cli", "app", "monorepo", "internal-service"}


@dataclass
class Finding:
    severity: str
    code: str
    line: int
    message: str


@dataclass
class Heading:
    level: int
    text: str
    line: int
    slug: str


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "").replace("**", "").strip().lower()
    chars = []
    for ch in text:
        if ch.isalnum() or ch in "-_":
            chars.append(ch)
        elif ch.isspace():
            chars.append("-")
    slug = "".join(chars)
    return slug


def strip_target(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    return target


def is_external(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(SKIP_SCHEMES) or not target


def parse_headings(lines: list[str], in_fence: list[bool]) -> list[Heading]:
    headings: list[Heading] = []
    for index, line in enumerate(lines):
        if in_fence[index]:
            continue
        match = HEADING_RE.match(line)
        if match:
            text = re.sub(r"\s+#+$", "", match.group(2)).strip()
            headings.append(
                Heading(
                    level=len(match.group(1)),
                    text=text,
                    line=index + 1,
                    slug=slugify(text),
                )
            )
    return headings


def fence_state(lines: list[str]) -> tuple[list[bool], list[tuple[int, str, str]]]:
    in_fence = [False] * len(lines)
    open_fences: list[tuple[int, str, str]] = []
    blocks: list[tuple[int, str, str]] = []
    current: tuple[int, str, str] | None = None
    for index, line in enumerate(lines):
        match = FENCE_RE.match(line)
        if current is None:
            if match:
                marker = match.group(1)[0]
                info = match.group(2).strip()
                current = (index + 1, marker, info)
                in_fence[index] = True
            continue
        in_fence[index] = True
        if match and match.group(1)[0] == current[1] and not match.group(2).strip():
            blocks.append(current)
            current = None
    if current is not None:
        open_fences.append(current)
    return in_fence, blocks


def heading_lookup(headings: list[Heading]) -> set[str]:
    return {heading.slug for heading in headings}


def section_present(headings: list[Heading], key: str) -> bool:
    if key == "title":
        return any(heading.level == 1 for heading in headings)
    aliases = SECTION_ALIASES[key]
    for heading in headings:
        lowered = heading.text.lower()
        if any(alias in lowered for alias in aliases):
            return True
    return False


def check_target(
    target: str,
    readme_dir: Path,
    repo_root: Path,
    line_no: int,
    findings: list[Finding],
    label: str,
) -> None:
    raw = strip_target(target)
    if is_external(raw) or "<" in raw or ">" in raw:
        return  # external or unresolved placeholder (reported separately)
    path_part, _, anchor = raw.partition("#")
    path_part = unquote(path_part)
    anchor = unquote(anchor)

    if not path_part:
        return  # anchor-only handled by TOC/heading checks

    if path_part.startswith("/"):
        resolved = (repo_root / path_part.lstrip("/")).resolve()
    else:
        resolved = (readme_dir / path_part).resolve()

    if not resolved.exists():
        findings.append(
            Finding(
                "error",
                "README008",
                line_no,
                f"Broken local {label}: `{raw}` -> {resolved}",
            )
        )
        return

    if label == "image" and resolved.is_file():
        size = resolved.stat().st_size
        if size > MAX_IMAGE_BYTES:
            findings.append(
                Finding(
                    "warning",
                    "README024",
                    line_no,
                    f"Local image is {size / 1024:.0f} KiB; compress or resize it before publishing",
                )
            )

    if anchor and resolved.suffix.lower() == ".md" and resolved.is_file():
        try:
            target_lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return
        target_in_fence, _ = fence_state(target_lines)
        target_headings = parse_headings(target_lines, target_in_fence)
        if anchor not in heading_lookup(target_headings):
            findings.append(
                Finding(
                    "warning",
                    "README023",
                    line_no,
                    f"Anchor `#{anchor}` not found in `{raw.split('#')[0]}`",
                )
            )


def collect_links(
    lines: list[str], in_fence: list[bool]
) -> list[tuple[int, str, str]]:
    links: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        if in_fence[index]:
            continue
        masked = line
        for match in BADGE_RE.finditer(line):
            links.append((index + 1, match.group(2), "image"))
            links.append((index + 1, match.group(3), "link"))
            masked = masked.replace(match.group(0), "")
        for match in IMAGE_RE.finditer(masked):
            links.append((index + 1, match.group(2), "image"))
        for match in INLINE_LINK_RE.finditer(masked):
            links.append((index + 1, match.group(2), "link"))
        for match in HTML_IMG_RE.finditer(masked):
            links.append((index + 1, match.group(1), "image"))
        ref_match = REF_DEF_RE.match(line)
        if ref_match:
            links.append((index + 1, ref_match.group(2), "link"))
    return links


def find_toc_range(
    headings: list[Heading], lines: list[str]
) -> tuple[Heading | None, int, int]:
    for index, heading in enumerate(headings):
        lowered = heading.text.lower()
        if "table of contents" in lowered or lowered in {"contents", "目录"}:
            end = len(lines)
            for following in headings[index + 1 :]:
                if following.level <= heading.level:
                    end = following.line - 1
                    break
            return heading, heading.line, end
    return None, 0, 0


def audit(path: Path, repo_root: Path, style: str) -> dict:
    findings: list[Finding] = []
    if not path.is_file():
        return {
            "file": str(path),
            "repo": str(repo_root),
            "style": style,
            "summary": {"errors": 1, "warnings": 0, "infos": 0, "lines": 0, "bytes": 0},
            "findings": [
                asdict(
                    Finding("error", "README001", 0, f"README not found or not a file: {path}")
                )
            ],
        }

    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    in_fence, blocks = fence_state(lines)
    headings = parse_headings(lines, in_fence)
    readme_dir = path.parent.resolve()
    repo_root = repo_root.resolve()

    if not text.strip():
        findings.append(Finding("error", "README002", 0, "README is empty"))

    if len(data) > MAX_GITHUB_BYTES:
        findings.append(
            Finding(
                "warning",
                "README020",
                0,
                f"README is {len(data) / 1024:.0f} KiB; GitHub truncates rendered content beyond 500 KiB",
            )
        )

    # Title and heading structure.
    h1s = [heading for heading in headings if heading.level == 1]
    if not h1s:
        findings.append(Finding("error", "README003", 0, "Missing level-1 title heading"))
    elif len(h1s) > 1:
        findings.append(
            Finding(
                "warning",
                "README004",
                h1s[1].line,
                "Multiple level-1 headings; keep one document title",
            )
        )

    previous: Heading | None = None
    for heading in headings:
        if previous and heading.level > previous.level + 1:
            findings.append(
                Finding(
                    "warning",
                    "README005",
                    heading.line,
                    f"Heading level jumps from H{previous.level} to H{heading.level}",
                )
            )
        previous = heading

    slugs = [heading.slug for heading in headings if heading.slug]
    duplicate_slugs = {slug for slug in slugs if slugs.count(slug) > 1}
    for heading in headings:
        if heading.slug in duplicate_slugs:
            findings.append(
                Finding(
                    "warning",
                    "README021",
                    heading.line,
                    f"Duplicate heading text `{heading.text}` produces an ambiguous anchor",
                )
            )

    # Empty sections.
    for index, heading in enumerate(headings):
        next_line = len(lines)
        for following in headings[index + 1 :]:
            next_line = following.line - 1
            break
        body = [
            line
            for line in lines[heading.line : next_line]
            if line.strip()
        ]
        if not body and index + 1 < len(headings):
            following = headings[index + 1]
            if following.level <= heading.level:
                findings.append(
                    Finding(
                        "warning",
                        "README022",
                        heading.line,
                        f"Empty section `{heading.text}`",
                    )
                )

    # Code fences.
    for start_line, _, info in blocks:
        if not info:
            findings.append(
                Finding(
                    "warning",
                    "README007",
                    start_line,
                    "Code fence has no language hint",
                )
            )
    # Recompute open fences for reporting (fence_state returns only closed blocks).
    current = None
    for index, line in enumerate(lines):
        match = FENCE_RE.match(line)
        if current is None:
            if match:
                current = (index + 1, match.group(1)[0])
        elif match and match.group(1)[0] == current[1]:
            current = None
    if current is not None:
        findings.append(
            Finding(
                "error",
                "README006",
                current[0],
                "Unclosed code fence",
            )
        )

    # Links and images.
    links = collect_links(lines, in_fence)
    seen = set()
    for line_no, target, label in links:
        key = (line_no, target, label)
        if key in seen:
            continue
        seen.add(key)
        check_target(target, readme_dir, repo_root, line_no, findings, label)

    # TOC presence and anchor validity.
    toc_heading, toc_start, toc_end = find_toc_range(headings, lines)
    if len(lines) >= 100 and toc_heading is None:
        findings.append(
            Finding(
                "warning",
                "README011",
                0,
                "README is 100+ lines but has no table of contents",
            )
        )
    if toc_heading is not None:
        valid_slugs = heading_lookup(headings)
        for line_no in range(toc_start, toc_end + 1):
            line = lines[line_no - 1] if line_no - 1 < len(lines) else ""
            for match in ANCHOR_LINK_RE.finditer(line):
                anchor = unquote(match.group(1) or match.group(2) or "")
                if anchor and anchor not in valid_slugs:
                    findings.append(
                        Finding(
                            "warning",
                            "README012",
                            line_no,
                            f"TOC anchor `#{anchor}` does not match any heading",
                        )
                    )

    # Anchor-only links outside the TOC.
    toc_lines = set(range(toc_start, toc_end + 1)) if toc_heading is not None else set()
    valid_slugs = heading_lookup(headings)
    for index, line in enumerate(lines):
        if in_fence[index] or index + 1 in toc_lines:
            continue
        for match in ANCHOR_LINK_RE.finditer(line):
            anchor = unquote(match.group(1) or match.group(2) or "")
            if anchor and anchor not in valid_slugs:
                findings.append(
                    Finding(
                        "warning",
                        "README009",
                        index + 1,
                        f"Anchor `#{anchor}` does not match any heading",
                    )
                )

    # First description / pitch.
    if headings:
        first_h1 = next((heading for heading in headings if heading.level == 1), None)
        if first_h1:
            first_h2_line = min(
                (
                    heading.line
                    for heading in headings
                    if heading.level >= 2 and heading.line > first_h1.line
                ),
                default=len(lines) + 1,
            )
            paragraph_lines: list[tuple[int, str]] = []
            found_list = False
            for index in range(first_h1.line, first_h2_line - 1):
                line = lines[index]
                if in_fence[index]:
                    continue
                stripped = line.strip()
                if not stripped:
                    if paragraph_lines:
                        break
                    continue
                if stripped.startswith("<!--") or stripped.startswith("</"):
                    continue
                if stripped.startswith("#"):
                    break
                if stripped.startswith(("[![", "![", "<")):
                    continue
                if stripped.startswith(("- ", "* ", "1. ")):
                    findings.append(
                        Finding(
                            "warning",
                            "README013",
                            index + 1,
                            "First content after the title is a list; add a one-sentence description first",
                        )
                    )
                    found_list = True
                    paragraph_lines = []
                    break
                paragraph_lines.append((index + 1, stripped))
            if paragraph_lines:
                first_line_no, first_line = paragraph_lines[0]
                if len(first_line) > 200:
                    findings.append(
                        Finding(
                            "warning",
                            "README013",
                            first_line_no,
                            "First description line is long; keep the pitch to one sentence (≤120 chars) and move detail below",
                        )
                    )
            elif first_h2_line <= len(lines) and not found_list:
                findings.append(
                    Finding(
                        "warning",
                        "README013",
                        first_h1.line,
                        "No description between the title and the first section",
                    )
                )

    # Badges without links and empty alt text.
    for index, line in enumerate(lines):
        if in_fence[index]:
            continue
        if ("shields.io" in line or "badge" in line.lower()) and IMAGE_RE.search(line):
            if not re.search(r"\[!\[", line):
                findings.append(
                    Finding(
                        "warning",
                        "README014",
                        index + 1,
                        "Badge image is not wrapped in a link",
                    )
                )
        for match in IMAGE_RE.finditer(line):
            if not match.group(1).strip():
                findings.append(
                    Finding(
                        "warning",
                        "README015",
                        index + 1,
                        "Image has empty alt text",
                    )
                )

    # Placeholders.
    for index, line in enumerate(lines):
        if in_fence[index] or line.lstrip().startswith("#"):
            continue
        placeholder_line = re.sub(r"`[^`]*`", "", line)
        for match in PLACEHOLDER_RE.finditer(placeholder_line):
            findings.append(
                Finding(
                    "warning",
                    "README016",
                    index + 1,
                    f"Unresolved placeholder `{match.group(0)}`",
                )
            )
        for match in ANGLE_PLACEHOLDER_RE.finditer(placeholder_line):
            token = match.group(1).strip()
            first_word = token.split()[0].split("/")[0].lower()
            if first_word in KNOWN_HTML_TAGS or token.startswith(("http", "//")):
                continue
            findings.append(
                Finding(
                    "warning",
                    "README016",
                    index + 1,
                    f"Unresolved placeholder `<{token}>`",
                )
            )

    # Style section coverage and license placement.
    for key in STYLE_SECTIONS.get(style, ()):
        if not section_present(headings, key):
            findings.append(
                Finding(
                    "warning",
                    "README010",
                    0,
                    f"Style `{style}` expects a section for `{key}` (aliases: {', '.join(SECTION_ALIASES[key][:4])})",
                )
            )

    license_headings = [
        heading
        for heading in headings
        if any(alias in heading.text.lower() for alias in SECTION_ALIASES["license"])
    ]
    if license_headings:
        license_heading = license_headings[0]
        later_siblings = [
            heading
            for heading in headings
            if heading.line > license_heading.line and heading.level <= license_heading.level
        ]
        if later_siblings:
            findings.append(
                Finding(
                    "warning",
                    "README017",
                    license_heading.line,
                    "License should be the last top-level section",
                )
            )
    if style in COMMAND_STYLES and not blocks:
        findings.append(
            Finding(
                "warning",
                "README019",
                0,
                "No fenced code block found; command-oriented READMEs need copy-paste examples",
            )
        )

    # Deduplicate identical findings caused by overlapping link regexes.
    unique: dict[tuple[str, str, int, str], Finding] = {}
    for finding in findings:
        unique[(finding.severity, finding.code, finding.line, finding.message)] = finding

    ordered = sorted(
        unique.values(),
        key=lambda finding: (
            {"error": 0, "warning": 1, "info": 2}.get(finding.severity, 3),
            finding.line,
            finding.code,
        ),
    )
    summary = {
        "errors": sum(1 for finding in ordered if finding.severity == "error"),
        "warnings": sum(1 for finding in ordered if finding.severity == "warning"),
        "infos": sum(1 for finding in ordered if finding.severity == "info"),
        "lines": len(lines),
        "bytes": len(data),
        "headings": len(headings),
        "code_blocks": len(blocks),
    }
    return {
        "file": str(path),
        "repo": str(repo_root),
        "style": style,
        "summary": summary,
        "findings": [asdict(finding) for finding in ordered],
    }


def print_text(result: dict) -> None:
    summary = result["summary"]
    print(f"README audit: {result['file']}")
    print(f"Style: {result['style']}")
    print(
        "Summary: "
        f"{summary['errors']} error(s), {summary['warnings']} warning(s), "
        f"{summary.get('infos', 0)} info(s); "
        f"{summary['lines']} lines, {summary['bytes']} bytes, "
        f"{summary.get('headings', 0)} headings, {summary.get('code_blocks', 0)} code blocks"
    )
    print()
    if not result["findings"]:
        print("No findings. README passes the deterministic checks.")
        return
    for finding in result["findings"]:
        location = f"{result['file']}:{finding['line']}" if finding["line"] else result["file"]
        print(f"[{finding['severity'].upper()}] {location} {finding['code']}: {finding['message']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit one or more README files.")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["README.md"],
        help="README paths (default: README.md). Multiple paths share one --style.",
    )
    parser.add_argument("--repo", default=None, help="Repository root (default: each README parent)")
    parser.add_argument("--style", choices=STYLES, default="generic", help="README style contract")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings too")
    return parser.parse_args(argv)


def aggregate_summary(results: list[dict]) -> dict:
    return {
        "files": len(results),
        "errors": sum(result["summary"]["errors"] for result in results),
        "warnings": sum(result["summary"]["warnings"] for result in results),
        "infos": sum(result["summary"].get("infos", 0) for result in results),
        "missing": sum(1 for result in results if not Path(result["file"]).is_file()),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    paths = [Path(raw).expanduser() for raw in args.paths]
    explicit_repo = Path(args.repo).expanduser() if args.repo else None

    results = []
    for path in paths:
        repo_root = explicit_repo if explicit_repo is not None else path.parent
        results.append(audit(path, repo_root, args.style))

    if args.format == "json":
        payload = results[0] if len(results) == 1 else {
            "summary": aggregate_summary(results),
            "files": results,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for index, result in enumerate(results):
            if index:
                print()
            print_text(result)
        if len(results) > 1:
            total = aggregate_summary(results)
            print()
            print(
                f"Total: {total['files']} file(s), {total['errors']} error(s), "
                f"{total['warnings']} warning(s), {total['missing']} missing"
            )

    total = aggregate_summary(results)
    if total["missing"]:
        return 2
    if total["errors"]:
        return 1
    if args.strict and total["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
