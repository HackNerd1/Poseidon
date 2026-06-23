# Module Review Guide

Use this reference when a review needs module-level architecture judgment rather than only line-level correctness.

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
