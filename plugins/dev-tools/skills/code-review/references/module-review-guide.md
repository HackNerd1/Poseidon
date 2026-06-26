# Module Review Guide

Use this reference when a review needs module-level architecture judgment rather than only line-level correctness.

## Dependency Census Workflow

When the change touches a shared module, public API, planner, runtime, registry, schema, hook, or command dispatcher, do a dependency census before concluding on blast radius.

Minimum questions:
- Who depends on this module?
- What does this module depend on?
- Which of those dependents did you actually inspect?
- Which tests cover those flows?

Preferred approach:
1. Run `scripts/dependency_census.py <module-path>` to get a first-pass census
2. Use repository search to verify imports, references, registrations, and call sites that look high-risk
3. Separate inbound dependents from outbound dependencies
4. Identify which inbound dependents are high-risk entry points
5. Inspect tests for the changed module and for the most important dependents
6. Report whether the census is exact, approximate, or sample-based

Output a short summary like:
- Module: `path/to/module`
- Fan-in: `N exact` or `approx N` or `sampled callers: A, B, C`
- Fan-out: `N exact` or `approx N`
- Inspected dependents: `...`
- Tests inspected: `...`
- Blind spots: `...`

## Core Signals

### Cohesion

Ask whether the file, class, or module has one clear purpose and one primary reason to change.

Flag:
- Mixed responsibilities such as business logic plus transport plus persistence plus formatting in one unit
- "Utility" modules that are turning into unrelated helper grab-bags
- APIs that operate on unrelated concepts or force callers to understand internal details

### Coupling

Ask whether the change increases unnecessary interdependence between modules.

Flag:
- New cross-layer imports, back-edges, and boundary violations
- Framework, storage, or transport details leaking into domain-level code
- Hidden coupling through globals, shared mutable state, implicit config, ambient context, or import-time side effects
- Temporal coupling where callers must invoke functions in a fragile order

### Fan-out

Ask how many modules this unit depends on and whether it is becoming a dependency hub.

Flag:
- Orchestration bloat
- Change amplification caused by too many outgoing dependencies
- Poor testability because too many collaborators must be mocked or configured

Suggested responses:
- Invert dependencies
- Split responsibilities
- Hide unstable details behind an adapter or interface

Do not stop at a qualitative statement like "high fan-out". Prefer one of:
- Exact count from repository search
- Approximate count with disclosed uncertainty
- Named sample of the outbound dependencies actually inspected

### Fan-in

Ask how many callers or dependents are affected by the change.

High fan-in means even a small diff may have large blast radius.

Review more strictly when changing:
- Public APIs
- Shared utilities
- Base classes
- Shared schemas
- Hooks
- Config helpers

Flag:
- Signature changes
- Semantic changes
- Default-value changes
- Error-behavior changes

Do not stop at "this is a high fan-in module". Prefer one of:
- Exact dependent list
- Approximate dependent count plus named critical callers
- Sample-based caller list with explicit blind spots

### Stability Heuristic

When rough counts are feasible, reason about stability using:

`instability = fan-out / (fan-in + fan-out)`

Interpretation:
- High fan-out and low fan-in implies a volatile component
- High fan-in components should expose smaller, more stable interfaces
- Stable layers should not depend on volatile ones unless the architecture explicitly allows it

## Architecture Erosion Signals

Explicitly check for:
- Cyclic dependencies
- Duplicate functionality introduced in a second module instead of extending the first
- Bypassing intended extension points, adapters, or facades
- "Just this once" shortcuts that weaken layer boundaries
- Shared modules absorbing unrelated responsibilities over time

## Scope Expansion Rules

Widen the review beyond the diff when the change touches:
- A public API
- A shared module
- A schema or config contract
- A high-fan-in utility
- A boundary between layers or services

Then inspect:
- Callers
- Tests
- Documentation
- Adjacent modules connected by imports or shared types

When time is limited, prioritize:
1. Entry points and user-triggered flows
2. Shared command/runtime/planner layers
3. Test files that should pin behavior
4. Docs or schemas that define the contract

## Architecture Finding Labels

For architecture findings, explicitly name one or more trigger signals:
- `Cohesion`
- `Coupling`
- `Fan-in`
- `Fan-out`
- `Cycle`
- `Boundary violation`
- `Duplicate functionality`
- `Over-engineering`

## Review Completeness Rule

A shared-module review is incomplete if it comments on blast radius, compatibility, or missing tests without stating what dependency census was actually performed.
