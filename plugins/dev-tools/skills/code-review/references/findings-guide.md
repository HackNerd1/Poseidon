# Findings Guide

Use this reference when writing review findings.

## Output Order

Present findings in this order:

1. Critical
2. Warnings
3. Suggestions

If no findings are discovered, say so explicitly and mention residual risks or testing gaps.

## Required Fields

Each finding should include:
- Category tag
- File path and line number when available
- Trigger signal for architecture findings
- Why it matters
- Concrete suggestion

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
