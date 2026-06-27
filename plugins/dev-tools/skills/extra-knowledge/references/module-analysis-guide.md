# Module Analysis Guide

Use this reference when dispatched as a sub-agent for **Step 2: Module Deep-Dive Analysis** — the per-module extraction of design patterns, technical decisions, and engineering insights worth learning.

## Input

You will receive:
- The **project overview** file path (from Step 1) — read this first for context
- Your **assigned module** name, path, and the core technical highlights flagged in the overview
- The **output directory** where your report should be saved

## Process

### Phase 1: Understand the Module

Before analyzing patterns, build a working mental model:

1. **Read the module's entry points** — index files, public API surfaces, main classes/functions
2. **Trace one key flow end-to-end** — pick the most important user action or data path and follow it through the module
3. **Map internal structure** — how does this module organize its own sub-components?
4. **Map external relationships** — what does it import? What imports it?
5. **Check tests** — test files reveal intended behavior, edge cases, and design assumptions

### Phase 2: Extract Learning Dimensions

For each dimension below, only include **non-trivial, genuinely instructive** content. Skip dimensions where the module is straightforward.

#### A. Architecture & Design Patterns

Identify **concrete, named or describable patterns** used in the module. For each:

- Pattern name (e.g., "Strategy Pattern", "Event-Driven Pipeline", "CQRS-lite")
- Where it appears (file:line range)
- What problem it solves in this specific context
- How it's implemented (key types, interfaces, wiring — 2-4 sentences)
- **Code example**: copy the **key implementation snippet** from the actual source code. Strip irrelevant details — remove comments, inline trivial helpers, collapse repetitive boilerplate. Keep variable names and core structure authentic. Use ` ```<lang> ` fenced code blocks.
- **Learning takeaway**: what makes this instance instructive?

Patterns to look for:

| Category | Examples |
|----------|----------|
| Creational | Factory, Builder, Singleton, Dependency Injection, Object Pool |
| Structural | Adapter, Facade, Decorator, Proxy, Composite |
| Behavioral | Observer, Strategy, Command, State Machine, Chain of Responsibility, Mediator |
| Architectural | Layered, Hexagonal/Ports & Adapters, CQRS, Event Sourcing, Pipeline, Plugin System, Microkernel |
| Concurrency | Actor Model, Worker Pool, Fan-out/Fan-in, Circuit Breaker, Bulkhead |

#### B. Code Organization & Conventions

Extract **non-obvious organizational patterns**:

- **Module boundary rules**: what belongs in this module vs. others? How is the boundary enforced?
- **Naming conventions**: any domain-specific naming patterns worth adopting?
- **File structure**: how are files grouped — by feature? by layer? by type?
- **Import discipline**: are there import ordering rules, barrel exports, or restricted internal imports?
- **Code generation**: any generated code? How is generation triggered and integrated?

#### C. Technical Decisions & Trade-offs

Flag decisions where **the rationale is visible or inferable**:

- Framework/library choice with visible trade-offs (e.g., "chose raw SQL over ORM for this query-heavy module because...")
- Data structure choices (e.g., "uses a Trie for prefix search instead of LIKE queries")
- Sync vs. async choices at boundaries
- Monolith vs. micro-service splits visible in code organization
- Schema design decisions (normalization level, indexing strategy, migration approach)

For each decision:
- What was chosen
- What was the alternative
- Visible evidence of the trade-off (performance, complexity, maintainability)
- **Learning takeaway**

#### D. Error Handling & Resilience

- **Error taxonomy**: does the module define its own error types/hierarchy?
- **Error propagation**: how do errors flow — exceptions? Result types? error codes? middleware?
- **Retry & fallback**: any retry logic, circuit breakers, graceful degradation?
- **Logging strategy**: what gets logged and at what level? Any structured logging conventions?
- **Input validation**: where does validation happen — at the boundary? in domain objects?

#### E. Testing Strategy

- **Test organization**: mirror source structure? separate `__tests__`? co-located?
- **Test patterns**: given-when-then? table-driven? property-based? snapshot?
- **Mocking philosophy**: mock at module boundary? mock nothing? use fakes?
- **Test utilities**: any custom test helpers, fixtures, or factories worth noting?
- **Coverage of edge cases**: which edge cases are explicitly tested? Which are deferred to integration tests?

#### F. Performance Patterns

- **Caching**: what's cached? at what layer? what's the invalidation strategy?
- **Lazy loading**: any deferred initialization, dynamic imports, or code splitting?
- **Batching / chunking**: any bulk operations, pagination, streaming?
- **Memoization**: any computed property caching, `useMemo`, `lru_cache`?
- **Connection / resource pooling**: any pooling of expensive resources?

#### G. Extensibility & Plugin Mechanisms

- **Extension points**: are there formal extension points (hooks, plugins, middleware, strategy interfaces)?
- **Registration patterns**: how do extensions register themselves? auto-discovery? manual registration? DI containers?
- **Versioning / compatibility**: any API versioning, deprecation patterns, or backward-compat shims?

#### H. Data Flow & State Management

- **State ownership**: who owns what state? Is there a single source of truth?
- **State transitions**: are transitions explicit (state machine) or implicit?
- **Data transformation pipeline**: how does data flow from input → validation → processing → output?
- **Immutability**: are data structures treated as immutable? Is there a copy-on-write pattern?

#### I. Visual Diagrams

Generate diagrams to help users quickly grasp the module's structure and flow. Use **Mermaid** syntax so diagrams render natively in markdown viewers.

##### IPO Diagram (required for every module)

Create an **Input-Process-Output table** that summarizes the module at a glance:

| Input | Process | Output |
|-------|---------|--------|
| `<data/event/config coming in>` | `<what the module does with it>` | `<result/side-effect produced>` |

- List 3-8 rows covering the module's primary responsibilities
- Input entries are nouns (data, events, config); Process entries are verbs (actions); Output entries are nouns (results, side effects)
- Each row should map to a concrete code path — annotate with file:line

##### Flow Diagram (required for modules with non-trivial internal flow)

Generate a **Mermaid flowchart** showing how data or control flows through the module's internal components. Choose the diagram type by what the module does:

| Module Characteristic | Diagram Type | Mermaid Syntax |
|----------------------|-------------|----------------|
| Multi-step pipeline / data transforms | Top-down flowchart | `flowchart TD` |
| Request routing / dispatch | Left-right flowchart | `flowchart LR` |
| Complex interaction with external modules | Sequence diagram | `sequenceDiagram` |
| Explicit state machine | State diagram | `stateDiagram-v2` |

**Node conventions:**
- `[Component Name]` — internal component / function group
- `[()]` — data store, cache, or database
- `{{}}` — external service or module
- `(())` — entry point
- `-->` — sync call, `-.->` — async/event, `-- text -->` — labeled edge

**Diagram rules:**
- Cap at **~15 nodes** — split complex flows into sub-diagrams if needed
- Annotate each node with the **source file** that implements it (use Mermaid `%%` comments or node labels)
- Reference the **code examples** from earlier sections — the diagram shows structure, the code snippets show implementation
- Keep it concrete — show real function/class names, not abstract layers

##### IPO + Flowchart Pairing

The IPO table and flowchart complement each other:
- **IPO** answers "what does it do?" — the module's contract
- **Flowchart** answers "how does it work?" — the internal orchestration

Place them together at the beginning of the report so users can orient themselves before reading the detailed analysis.

### Phase 3: Write the Report

Save to `<output_dir>/modules/<module-slug>.md`. The file MUST follow this structure:

```markdown
# Module Analysis: <module-name>

> Path: `<module-path>` | Language: <lang> | Files: ~<N>

## Module Summary

<2-3 sentences on what this module does and its role in the project>

## Dependency Context

- **Depends on**: <list of module-internal and external dependencies>
- **Depended on by**: <list of callers / consumers>
- **Fan-in**: <approximate count> | **Fan-out**: <approximate count>

---

## IPO & Flow Diagram

### IPO (Input-Process-Output)

| Input | Process | Output |
|-------|---------|--------|
| `<data/event>` | `<action — reference code snippet below>` | `<result>` |
| ... | ... | ... |

### Flow Diagram

```mermaid
flowchart TD
  %% Choose diagram type based on module characteristics
  %% Annotate nodes with source file paths
  Entry([entry point]) --> Core[Core Component<br/>file.ts]
  Core --> Store[()]Cache / DB
  Core -.-> External{{External Service}}
```

> The IPO table shows what the module does; the flowchart shows how it works internally. Each node maps to a code example in the sections below.

---

## 1. Architecture & Design Patterns

### <Pattern Name>
- **Location**: `<file>:<line-range>`
- **Problem it solves**: <one sentence>
- **Implementation**: <key types, interfaces, and how they connect — 2-4 sentences>
- **Code example**:
  ```<lang>
  <key snippet from actual source, stripped of irrelevant details>
  ```
- **Learning takeaway**: <why this instance is instructive — 1-2 sentences>

> Repeat for each significant pattern found.

---

## 2. Code Organization & Conventions

<Describe non-obvious organizational patterns — if the module is straightforward CRUD, say so concisely.>

---

## 3. Technical Decisions & Trade-offs

### <Decision Title>
- **Choice**: <what was chosen>
- **Alternative considered**: <the other path — infer if not documented>
- **Visible trade-off**: <evidence in the code — 1-2 sentences>
- **Code example** (if the decision manifests in a specific code structure):
  ```<lang>
  <key snippet from actual source, stripped of irrelevant details>
  ```
- **Learning takeaway**: <1-2 sentences>

> Repeat for each significant decision found.

---

## 4. Error Handling & Resilience

<How errors are defined, propagated, logged, and recovered in this module. Skip if standard.>

---

## 5. Testing Strategy

<Test organization, patterns, and notable practices. Include file paths.>

---

## 6. Performance Patterns

<Non-obvious performance techniques. Skip if none found.>

---

## 7. Extensibility Mechanisms

<How the module supports extension, if applicable.>

---

## 8. Data Flow & State Management

<How data and state are managed within this module.>

---

## 9. Key Learnings Summary

<3-5 bullet points distilling the most valuable engineering insights from this module. These should be actionable — things a developer could apply to their own projects.>

---

## 10. Blind Spots

<What you couldn't fully assess and why — e.g., "runtime behavior not visible from static analysis", "integration tests not inspected", "external service interactions unknown">
```

## Key Rules

1. **Read actual code** — never guess a pattern from file names alone; read the source files
2. **IPO diagram first** — every module report MUST start with an IPO table; it gives readers instant orientation before diving into details
3. **Flowchart for non-trivial flow** — if the module has multiple internal components or a multi-step pipeline, add a Mermaid flowchart below the IPO; keep it under ~15 nodes and annotate nodes with source files
4. **Include code examples** — every significant pattern or decision MUST include a code snippet copied from the actual source; strip irrelevant details but keep structure and naming authentic
5. **Quality over quantity** — 3 well-explained patterns with code are better than 10 shallow mentions without
6. **Contextualize** — explain *why* a pattern matters in this specific codebase, not just what it is
7. **Be honest about blind spots** — state what you couldn't verify
8. **Connect to the overview** — reference the project overview's technical highlights when relevant
9. **Write for learning** — the reader wants to learn from this codebase; explain what makes each finding instructive
10. **Skip the obvious** — don't document standard framework usage ("uses React hooks") unless the usage is notably instructive
11. **Estimate fan-in/fan-out** — approximate counts are fine; note when exact
