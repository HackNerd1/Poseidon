---
name: code-review
description: 'Review staged/unstaged code changes, documentation, and architecture alignment. Triggers when users ask to "review code", "code review", "review staged", "review diff", "check changes", or provide a PR/patch for review. Covers correctness bugs, doc-code mismatch, architecture compliance, and web-informed best practices. Use cases: pre-commit review, architecture doc change validation, PR review, diff inspection.'
---

# Code Review Skill

## Overview

You will conduct a structured code review covering correctness, architecture alignment, and documentation consistency. Core principle: **verify against ground truth — read the actual code, search the web for standards, and check architecture docs before forming conclusions**.

## Workflow

### Step 1: Determine Review Scope

Ask the user or infer from context what to review. In priority order:

1. **User-specified target** — a file path, commit hash, PR URL, or branch name
2. **Staged changes** — `git diff --cached` (the default when the user says "review staged code")
3. **Unstaged changes** — `git diff` (when the user says "review my changes")
4. **Recent commits** — `git log --oneline -5` (when no working-tree changes exist)

If scope is ambiguous, ask:

> What should I review? Options: staged changes, unstaged changes, a specific file, or a commit/PR?

Once determined, load the full diff with `git diff` or `git diff --cached` as appropriate. For PRs, use `gh pr view` or `gh pr diff`.

### Step 2: Classify Changes

Scan the diff and classify every changed file into one of three categories:

| Category | Signal | Review Strategy |
|----------|--------|-----------------|
| **Documentation** | `*.md`, `*.rst`, `*.txt`, `docs/**` | Verify doc-code consistency, architecture rationality, web-search for standards |
| **Source code** | `*.ts`, `*.tsx`, `*.js`, `*.py`, `*.go`, `*.java`, etc. | Check against ARCHITECTURE.md / design docs, assess complexity, flag test gaps |
| **Config / infra** | `*.json`, `*.yaml`, `*.yml`, `*.toml`, `Dockerfile`, CI files | Validate syntax, check for secrets exposure, verify environment parity |

### Step 3: Review by Category

#### 3A. Documentation Changes

For each changed document:

1. **Doc-code consistency** — do claims in the doc match what the code actually does?
   - Grep for referenced functions, classes, APIs, file paths, config keys
   - Verify they exist and behave as described
2. **Architecture rationality** — does the described design follow established patterns?
   - If uncertain about a pattern or standard, **search the web** before concluding
   - Compare against the project's own `ARCHITECTURE.md` or equivalent
3. **Structural conformance** — does the doc follow the project's documentation conventions (e.g., SKILL.md format defined in `docs/architecture.md`)?
4. **Completeness** — are there gaps, stale references, or missing sections?

#### 3B. Source Code Changes

For each changed source file:

1. **Architecture alignment** — check whether the change respects:
   - The project's `ARCHITECTURE.md` or `docs/architecture.md`
   - Module boundaries and dependency direction
   - Naming conventions and code organization patterns
2. **Correctness** — look for:
   - Null / undefined access, missing error handling at system boundaries
   - Race conditions (shared mutable state, missing awaits)
   - Resource leaks (unclosed handles, listeners, timers)
   - Logic errors (inverted conditions, off-by-one, wrong operator)
3. **Complexity assessment** — rate the change:

   | Level | Criteria | Action |
   |-------|----------|--------|
   | **High** | New module, >200 lines, state machine, async coordination, threading, security/auth, data migration | **Must ask**: "This is a complex change. Should I generate unit tests for the new logic?" |
   | **Medium** | New function >20 lines, modified algorithm, new API endpoint, config schema change | **Ask**: "This is moderately complex. Would you like me to generate unit tests?" |
   | **Low** | Typo fix, logging, constant update, <10 line change, comment edit | No test prompt needed |

   Additionally, check if the changed code is in a **high-traffic path** (frequently called function, shared utility, core module). If so, upgrade the complexity one level.
4. **Web-informed review** — when you encounter an unfamiliar pattern, library API, or security-sensitive code (auth, crypto, permissions), **search the web** for current best practices before concluding. Include search results as context in your findings.

#### 3C. Config / Infra Changes

1. **Syntax validity** — does the diff introduce malformed JSON/YAML?
2. **Secrets check** — flag any hardcoded tokens, passwords, API keys, or private URLs
3. **Environment drift** — does a config change in one environment have a matching change in others?

### Step 4: Present Findings

After review, output a **findings list** organized by severity:

```
## Review Findings

### Critical (must fix before merge)
- [Category] Description of issue — file:line
  - Why it matters: <impact>
  - Suggestion: <concrete fix>

### Warnings (should fix, may indicate deeper issues)
- [Category] Description — file:line
  - Why it matters: <impact>
  - Suggestion: <concrete fix>

### Suggestions (nice to have, non-blocking)
- [Category] Description — file:line
  - Why it matters: <impact>
  - Suggestion: <concrete fix>
```

Each finding must include:
- **Category tag**: `[Correctness]`, `[Architecture]`, `[Doc-Code]`, `[Security]`, `[Performance]`, `[Style]`, `[Testing]`
- **File path and line number** (where applicable)
- **Why it matters** — one sentence on the concrete impact
- **Suggestion** — one sentence on what to change

If you searched the web during review, cite the URLs that informed your conclusions.

### Step 5: Wait for User Decision

After presenting findings, ask:

> Would you like me to help fix any of these issues? I can apply the fixes in order of severity — from critical down to suggestions.

Do NOT modify code until the user confirms which issues to fix.

### Step 6: Apply Fixes & Verify

Once the user selects issues to fix:

1. Apply changes one file at a time, explaining each edit
2. After all fixes are applied, **run the project's existing tests** if available:
   - Check for `package.json` scripts, `Makefile`, `tox.ini`, `pytest`, `go test`, etc.
   - Run the relevant test suite and report results
3. If no test suite exists, provide a manual **verification checklist**:

```
## Verification Checklist
- [ ] <specific scenario from the diff> works as expected
- [ ] <related feature> still functions correctly
- [ ] No new errors in console / terminal output
- [ ] Edge case: <specific edge case> handled correctly
```

### Step 7: Commit Message

After all fixes are verified and the checklist/tests pass, ask:

> All issues resolved and verified. Would you like me to generate a commit message?

- **User says yes**: generate a concise, well-structured commit message following the repo's commit style (check `git log --oneline -3` for convention). Present the draft for user approval before committing.
- **User says no**: end the review session.

## Key Rules

1. **Read before judging** — always read the actual files referenced in the diff; never guess from filenames alone
2. **Search when uncertain** — if a pattern, library, or standard is unfamiliar, search the web before drawing conclusions
3. **Architecture doc is authoritative** — `ARCHITECTURE.md` / `docs/architecture.md` is the ground truth for design compliance
4. **Severity, not quantity** — a single well-explained critical finding is better than ten nitpicks
5. **No unsolicited edits** — present findings first, fix only after user confirmation
6. **Test before done** — always attempt to run existing tests after applying fixes
7. **Commit only on request** — never commit without user approval

## Edge Cases

- **No changes to review** — tell the user: "Nothing to review — the working tree and staging area are clean."
- **Binary files in diff** — skip content review, only flag if the binary is unexpectedly large or in a sensitive path
- **Merge conflicts in diff** — flag them as critical and suggest resolving before review continues
- **Very large diff (>500 lines)** — summarize by module/theme rather than listing every finding individually; offer to deep-dive on specific files
- **No ARCHITECTURE.md exists** — skip architecture-alignment checks; note this as a suggestion to create one
- **User asks to review a PR** — use `gh pr view <url>` and `gh pr diff <url>` to fetch the PR content

## Limitations

- Not a replacement for CI linting — style-only issues (indentation, line length, formatting) are skipped unless they affect readability
- Not a replacement for security audit — can flag obvious secrets and injection patterns but not a full threat model
- Not a replacement for performance profiling — can flag obvious N+1 queries or O(n²) patterns but not micro-benchmarks
- Cannot review compiled binaries, images, or other non-text assets
