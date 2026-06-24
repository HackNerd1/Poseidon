# Findings Guide

Use this reference when writing review findings.

## Output Order

Present findings in this order:

1. Critical
2. Warnings
3. Suggestions

If no findings are discovered, say so explicitly and mention residual risks or testing gaps.

For architecture-heavy or shared-module reviews, add a short `Architecture Coverage` block before or after findings.

## Required Fields

Each finding should include:
- Category tag
- File path and line number when available
- Trigger signal for architecture findings
- Why it matters
- Concrete suggestion

## Architecture Coverage Block

Use this block when the review discusses fan-in, fan-out, blast radius, shared modules, planners, runtimes, registries, or public APIs.

Include:
- Module reviewed
- Fan-in status: exact / approximate / sample-based
- Fan-out status: exact / approximate / sample-based
- Inbound dependents inspected
- Outbound dependencies inspected
- Tests inspected
- Blind spots or unreviewed callers

Example:

```md
## Architecture Coverage
- Module: `src/runtime/useTimelineCommandRuntime.ts`
- Fan-in: approximate, 5 callers found via repo search
- Fan-out: exact, 7 direct imports
- Inbound dependents inspected: `useTimelineResourceDrop`, `useTimelineClipInteractions`, `useTimelineCommandActions`
- Outbound dependencies inspected: `timelineCommands/assembly`, `history`, `selection`
- Tests inspected: `useTimelineCommandRuntime.test.ts`, `timelineCommands.test.ts`
- Blind spots: no direct test found for `planClipPasteAssembly`
```

## Category Tags

Use one of:
- `[Correctness]`
- `[Architecture]`
- `[Doc-Code]`
- `[Security]`
- `[Performance]`
- `[Style]`
- `[Testing]`

## Severity Guidance

### Critical

Use when the issue can cause:
- Incorrect behavior
- Crash or data loss
- Security exposure
- Architecture breakage with high blast radius
- Merge blocking reviewability issues such as unresolved conflicts

### Warnings

Use when the issue should be fixed soon because it increases:
- Regression risk
- Maintenance cost
- Architectural drift
- Test fragility
- Compatibility risk in shared modules

### Suggestions

Use when the issue is non-blocking but likely worth improving for:
- Clarity
- Simpler design
- Better test shape
- Reduced future coupling

## Writing Guidance

- Be specific and concrete
- Explain impact, not only preference
- Prefer one strong issue over many weak nits
- For design comments, explain whether the problem is cohesion, coupling, fan-in, fan-out, cycle creation, boundary violation, or over-engineering
- When a change mixes behavior and broad formatting churn, call out the reviewability risk explicitly
- Distinguish clearly between exact dependency counts and sampled caller inspection; do not imply precision you did not establish
