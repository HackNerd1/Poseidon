---
name: code-review
description: 'Review staged/unstaged code changes, documentation, and architecture alignment using first principles. Triggers when users ask to "review code", "code review", "review staged", "review diff", "check changes", or provide a PR/patch for review. Covers correctness bugs, redundant design, doc-code mismatch, architecture compliance, and web-informed best practices. Use cases: pre-commit review, architecture doc change validation, PR review, diff inspection.'
---

# Code Review Skill

## Overview

You will conduct a structured code review grounded in **first principles**: start from what the change must actually do, then check whether the code is necessary, correct, and aligned with existing boundaries. Do not over-interpret metrics, intent, or future needs.

Core principle: **verify against ground truth — read the actual code and neighbors, check architecture docs, and only then judge. Prefer evidence over speculation.**

## Core Responsibilities

1. Determine review scope from user intent, working tree, or PR target.
2. Review changed code/docs against actual implementation and module boundaries.
3. Identify correctness, architecture, redundant design, testing, and reviewability risks with severity.
4. State findings in concise language: problem, reason, suggestion.
5. Fix only after user confirmation; verify with tests or a concrete checklist.

## First Principles (mandatory)

Before writing any finding, answer briefly (internally or in Architecture Coverage):

1. **What is the actual job?** — what observable behavior or contract must this change deliver?
2. **What is necessary?** — which modules, APIs, and dependencies are required for that job?
3. **What is added beyond necessity?** — extra layers, abstractions, options, or parallel paths without a current caller/need?
4. **What evidence supports the claim?** — file/line, caller list, failing path, or doc mismatch — not “feels wrong” or future speculation

Rules:
- Do **not** invent requirements the change did not claim to solve
- Do **not** treat fan-in/fan-out/instability numbers as conclusions; they are investigation signals
- Do **not** demand generality “for later”
- Prefer the smallest design that satisfies the actual job and existing architecture

## Input Requirements

- Accept: staged diff, unstaged diff, file path, commit hash, branch, or PR URL
- If scope unspecified: `git diff --cached` → `git diff` → recent commits
- Read the full changed file before concluding
- Widen to callers/tests/docs when touching public API, shared module, interface, schema, or architectural seam

## Output Format

Follow `references/findings-guide.md` (readable report for the user):

- Lead with **Scope** + **Summary** (counts + verdict)
- Then severity sections with **numbered** findings
- Each finding: `[Category] Title` → Where / Issue / Why / Fix (Trigger only for architecture / redundancy)
- Skip empty severity sections (keep `Critical: None.` when lower findings exist)
- Architecture Coverage after findings when reviewing shared modules / public APIs / planners / runtimes / registries / schemas / hooks / dispatch layers
- If no findings: say so in Summary, plus residual risks or test gaps
- Do not edit code until the user confirms what to fix

## Reference Loading Rules

- Module / dependency review → `references/module-review-guide.md`
- Redundant design check → `references/redundant-design.md`
- Severity and wording → `references/findings-guide.md`
- External heuristics when repo-local guidance is insufficient → `references/public-review-heuristics.md`
- Shared module / seam → run `scripts/dependency_census.py` before manual caller sampling
- Load only what the current review needs

## Workflow

### Step 1: Determine Review Scope

Priority:

1. User-specified target
2. Staged — `git diff --cached`
3. Unstaged — `git diff`
4. Recent commits — `git log --oneline -5`

If ambiguous, ask:

> What should I review? Options: staged changes, unstaged changes, a specific file, or a commit/PR?

Load the full diff (`git diff` / `git diff --cached`; PRs via `gh pr view` / `gh pr diff`).

Context before judging:

1. Read the full changed file, not only the hunk
2. Read direct neighbors when interfaces, shared types, utilities, or boundaries change
3. If public API / shared / high fan-in → widen to callers / tests / docs
4. Dependency census for shared modules or seams:
   - Who depends on this?
   - What does it depend on?
   - Which dependents were inspected?
   - Which tests cover those paths?
5. State whether fan-in / fan-out reasoning is **exact**, **approximate**, or **sample-based**

### Step 2: Classify Changes

| Category | Signal | Review Strategy |
|----------|--------|-----------------|
| **Documentation** | `*.md`, `*.rst`, `*.txt`, `docs/**` | Doc-code consistency, architecture rationality, standards search if needed |
| **Source code** | `*.ts`, `*.tsx`, `*.js`, `*.py`, `*.go`, `*.java`, etc. | Correctness, first-principles necessity, architecture, tests |
| **Config / infra** | `*.json`, `*.yaml`, `*.yml`, `*.toml`, `Dockerfile`, CI | Syntax, secrets, environment parity |

### Step 3: Review by Category

#### 3A. Documentation Changes

1. **Doc-code consistency** — claims match real code (grep symbols/paths/keys)
2. **Architecture rationality** — compare to project architecture; search web only when uncertain
3. **Structural conformance** — follow project doc conventions
4. **Completeness** — gaps, stale refs, missing sections

#### 3B. Source Code Changes

For each changed source file:

1. **First-principles necessity** — from the four questions above: is the design the smallest that does the job?
2. **Redundant design** — load `references/redundant-design.md`. Flag only with evidence of current unused / duplicated / speculative structure
3. **Architecture alignment** — `ARCHITECTURE.md` / `docs/architecture.md`, module boundaries, dependency direction, naming/organization
4. **Module quality** — cohesion, coupling, fan-in/out, cycles, boundary violations (same guide). Use metrics as signals, not verdicts
5. **Correctness**:
   - Null / undefined; missing boundary error handling
   - Races (shared mutable state, missing awaits)
   - Resource leaks
   - Logic errors (inverted conditions, off-by-one, wrong operator)
6. **Complexity / test prompt** — rate the change:

   | Level | Criteria | Action |
   |-------|----------|--------|
   | **High** | New module, >200 lines, state machine, async coordination, threading, security/auth, data migration | Ask whether to generate unit tests |
   | **Medium** | New function >20 lines, modified algorithm, new API endpoint, config schema change | Ask whether to generate unit tests |
   | **Low** | Typo, logging, constant, <10 lines, comment | No test prompt |

   High-traffic path → upgrade one level.
7. **Tests and blast radius** — coverage proportional to risk; shared/boundary changes need more than local unit tests
8. **Web-informed review** — only for unfamiliar patterns, security-sensitive code, or real tradeoffs; cite URLs used

#### 3C. Config / Infra Changes

1. Syntax validity
2. Secrets (tokens, passwords, keys, private URLs)
3. Environment drift across envs

### Step 4: Present Findings

```md
## Review Findings

**Scope:** <target> — <one-line what changed>
**Summary:** <e.g. No critical issues; 1 warning, 2 suggestions>

### Critical
None.

### Warnings

1. **[Category] Short title**
   - Where: `file:line`
   - Trigger: `<signal>`   # architecture / redundancy only
   - Issue: <one line>
   - Why: <one line>
   - Fix: <one line>

### Suggestions

1. **[Category] Short title**
   - Where: `file:line`
   - Issue: <one line>
   - Why: <one line>
   - Fix: <one line>

### Residual risks
- <optional>
```

Category tags: `[Correctness]`, `[Architecture]`, `[Redundancy]`, `[Doc-Code]`, `[Security]`, `[Performance]`, `[Style]`, `[Testing]`

Load `references/findings-guide.md` for full layout rules, severity, and wording.
For shared-module / architecture-heavy reviews, append Architecture Coverage from `references/module-review-guide.md`.

Cite web URLs if used.

### Step 5: Wait for User Decision

> Would you like me to help fix any of these issues? I can apply the fixes in order of severity — from critical down to suggestions.

Do not modify code until the user confirms which issues to fix.

### Step 6: Apply Fixes & Verify

1. Apply one file at a time, briefly explain each edit
2. Run existing project tests when available; report results
3. If no suite, give a short verification checklist tied to the diff

### Step 7: Commit Message

After verification, ask whether to draft a commit message. Draft only on yes; commit only on explicit approval. Follow repo commit style (`git log --oneline -3`).

## Key Rules

1. **First principles before labels** — state the actual job and necessity before applying cohesion/coupling tags
2. **No over-interpretation** — no speculative future requirements; no metric-as-verdict
3. **Read before judging** — real files, not filenames alone
4. **Search when uncertain** — unfamiliar pattern/library/standard → search before concluding
5. **Architecture doc is authoritative** for design compliance when present
6. **Review in system context** for interface / shared / seam changes
7. **Design before style** — correctness, necessity, tests, maintainability over nits
8. **Severity over quantity** — one clear critical finding beats ten weak nits
9. **Readable findings** — Scope/Summary first; Issue / Why / Fix one line each
10. **No unsolicited edits** — present first, fix after confirmation
11. **Test after fixes** — run existing tests when possible
12. **Commit only on request**

## Edge Cases

- **No changes** — working tree and staging clean → say so
- **Binary files** — skip content; flag unexpected size/sensitive path
- **Merge conflicts** — Critical; resolve before continuing
- **Very large diff (>500 lines)** — summarize by module/theme; offer deep-dives
- **No ARCHITECTURE.md** — skip alignment checks; suggest creating one
- **PR review** — `gh pr view` / `gh pr diff`
- **“Pure refactor”** — verify signatures, defaults, side effects, error semantics actually unchanged
- **Shared-module change** — require callers/tests/docs checks even for small diffs
- **Shared-module without census** — incomplete; add census or disclose sample-based inspection
- **Formatting + logic mixed** — flag reviewability; ask to split if needed

## Limitations

- Not a CI linter replacement — skip pure formatting unless it hurts readability
- Not a full security audit or performance profile
- Cannot review compiled binaries / images / non-text assets

## Reference Notes

- `references/public-review-heuristics.md` only when repo-local guidance is insufficient or external standards materially affect the review
