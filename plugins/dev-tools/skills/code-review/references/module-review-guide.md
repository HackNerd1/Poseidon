# Module Review Guide

Use when the review needs module-level judgment, not only line-level correctness.

## First Principles First

Apply the First Principles section in `../SKILL.md` before cohesion / coupling / fan metrics. Metrics are investigation aids, not automatic findings.

## Redundant Design

For unused / duplicated / speculative structure, load and follow `redundant-design.md` (do not re-derive the checklist here).

## Dependency Census Workflow

When the change touches a shared module, public API, planner, runtime, registry, schema, hook, or command dispatcher, do a dependency census before concluding on blast radius.

Minimum questions:
- Who depends on this module?
- What does this module depend on?
- Which of those dependents did you actually inspect?
- Which tests cover those flows?

Preferred approach:
1. Run `scripts/dependency_census.py <module-path>` for a first-pass census
2. Verify high-risk imports, registrations, and call sites via repository search
3. Separate inbound dependents from outbound dependencies
4. Inspect tests for the changed module and critical dependents
5. Report whether the census is exact, approximate, or sample-based

Output a short summary:
- Module: `path/to/module`
- Fan-in: `N exact` / `approx N` / `sampled callers: A, B, C`
- Fan-out: `N exact` / `approx N`
- Inspected dependents: `...`
- Tests inspected: `...`
- Blind spots: `...`

## Core Signals

### Cohesion

Ask: one clear purpose and one primary reason to change?

Flag:
- Mixed responsibilities (e.g. business + transport + persistence + formatting in one unit)
- “Utility” grab-bags of unrelated helpers
- APIs that force callers to know internals or unrelated concepts

### Coupling

Ask: does the change add **unnecessary** interdependence?

Flag:
- Cross-layer imports, back-edges, boundary violations
- Framework / storage / transport details leaking into domain code
- Hidden coupling via globals, shared mutable state, implicit config, ambient context, import-time side effects
- Temporal coupling that requires fragile call order

### Fan-out

Ask: are outbound dependencies necessary for the job, or is this becoming a hub?

Flag when necessity fails:
- Orchestration bloat
- Change amplification from too many outgoing deps
- Poor testability (too many collaborators to configure)

Responses when justified: invert dependencies, split responsibilities, or hide unstable details behind an existing adapter/interface — do not invent a new abstraction layer without a current second use.

Prefer exact / approximate / named-sample counts over “high fan-out” alone.

### Fan-in

High fan-in → small diffs can have large blast radius. Review shared APIs, utilities, base classes, schemas, hooks, and config helpers more strictly.

Flag real contract shifts:
- Signature / semantic / default / error-behavior changes

Prefer exact / approximate / sample-based dependent lists with blind spots stated.

### Stability (optional)

Only when counts are reliable enough to discuss:

`instability = fan-out / (fan-in + fan-out)`

Use as a soft hint:
- High fan-in modules should stay small and stable at the interface
- Stable layers should not depend on volatile ones unless architecture allows it

Do **not** compute or cite this formula when fan counts are sample-based or highly uncertain — that is over-interpretation.

## Architecture Erosion Signals

Check:
- Cyclic dependencies
- Bypassing intended extension points, adapters, or facades
- “Just this once” shortcuts that weaken layer boundaries
- Shared modules absorbing unrelated responsibilities over time
- Redundant design signals from `redundant-design.md` (especially duplicates and parallel modules)

## Scope Expansion Rules

Widen beyond the diff when touching:
- Public API, shared module, schema/config contract, high-fan-in utility, or layer/service boundary

Then inspect callers, tests, docs, and adjacent modules connected by imports or shared types.

When time is limited, prioritize:
1. Entry points and user-triggered flows
2. Shared command / runtime / planner layers
3. Tests that should pin behavior
4. Docs or schemas that define the contract

## Architecture Finding Labels

Name one or more trigger signals:
- `Cohesion`
- `Coupling`
- `Fan-in`
- `Fan-out`
- `Cycle`
- `Boundary violation`
- `Redundant design`

## Review Completeness Rule

A shared-module review is incomplete if it comments on blast radius, compatibility, or missing tests without stating what dependency census was actually performed.
