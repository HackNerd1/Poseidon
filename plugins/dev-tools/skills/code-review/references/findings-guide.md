# Findings Guide

Use when writing review findings. Optimize for **scanability**: summary first, then numbered items the reader can jump through.

## Report Skeleton

```md
## Review Findings

**Scope:** <staged | unstaged | PR #N | path/commit> — <one-line what changed>
**Summary:** <one sentence: counts by severity + overall verdict>

### Critical
None.

### Warnings

1. **[Architecture] Title in plain language**
   - Where: `path/to/file.ts:42`
   - Trigger: `Fan-in` _(only for architecture / redundancy)_
   - Issue: <what is wrong — one line>
   - Why: <why it matters — one line>
   - Fix: <what to change — one line>

### Suggestions

1. **[Redundancy] Title in plain language**
   - Where: `path/to/file.ts:10-20`
   - Trigger: `Redundant design`
   - Issue: ...
   - Why: ...
   - Fix: ...

### Residual risks
- <gap, untested path, or sample-based blind spot — or omit section if none>
```

## Layout Rules

1. **Scope + Summary first** — reader knows what was reviewed and how bad it is before details
2. **Severity order** — Critical → Warnings → Suggestions
3. **Skip empty severity sections** — except when there are lower findings and Critical is clean, keep `### Critical` with `None.` so the top risk is obvious
4. **Number findings** within each severity (`1.`, `2.`, …)
5. **Title line** = `[Category]` + short plain-language title (not the full Issue sentence)
6. **Where** on its own line with path/line (multiple paths OK, comma-separated or bulleted under Where)
7. **Trigger** only for architecture / redundancy findings; omit otherwise
8. **Issue / Why / Fix** — one line each; no multi-paragraph essays
9. **No findings** → say so under Summary, skip severity sections, still list Residual risks / test gaps if any
10. **Architecture Coverage** (when needed) goes **after** findings, not before

## Field Meanings

| Field | Meaning |
|-------|---------|
| Title | Scannable label for the finding |
| Where | File path and line (or range) |
| Trigger | `Cohesion`, `Coupling`, `Fan-in`, `Fan-out`, `Cycle`, `Boundary violation`, `Redundant design` |
| Issue | What is wrong |
| Why | Impact or root cause |
| Fix | Concrete change (prefer delete/merge/move over “consider refactoring”) |

No speculative “might someday” wording unless the risk is evidenced now.

## Architecture Coverage Block

Use when discussing fan-in, fan-out, blast radius, shared modules, planners, runtimes, registries, or public APIs.

```md
## Architecture Coverage
- Module: `src/runtime/useTimelineCommandRuntime.ts`
- Fan-in: approximate, 5 callers found via repo search
- Fan-out: exact, 7 direct imports
- Inbound inspected: `useTimelineResourceDrop`, `useTimelineClipInteractions`, `useTimelineCommandActions`
- Outbound inspected: `timelineCommands/assembly`, `history`, `selection`
- Tests inspected: `useTimelineCommandRuntime.test.ts`, `timelineCommands.test.ts`
- Blind spots: no direct test for `planClipPasteAssembly`
```

## Category Tags

Use one of:
- `[Correctness]`
- `[Architecture]`
- `[Redundancy]`
- `[Doc-Code]`
- `[Security]`
- `[Performance]`
- `[Style]`
- `[Testing]`

Use `[Redundancy]` for unused / duplicated / speculative structure (see `redundant-design.md`). Use `[Architecture]` when the primary issue is boundary, cycle, cohesion, or coupling with current dependents.

## Severity Guidance

### Critical

- Incorrect behavior, crash, or data loss
- Security exposure
- Architecture breakage with high blast radius
- Merge-blocking reviewability issues (e.g. unresolved conflicts)

### Warnings

Should fix soon because it increases:
- Regression risk
- Maintenance cost
- Architectural drift
- Redundant / divergent paths
- Test fragility
- Compatibility risk in shared modules

### Suggestions

Non-blocking but worth improving for clarity, simpler necessary design, better tests, or lower future coupling.

## Writing Guidance

- Be specific: name the symbol, contract, or dependency
- Impact over preference
- One strong issue over many weak nits
- Do not over-interpret: if evidence is only a sampled caller list, say so
- When behavior and broad formatting churn mix, call out reviewability risk
- Prefer concrete deletes/merges/moves in Fix over vague “consider refactoring”
