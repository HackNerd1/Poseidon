# Project Survey Guide

Use this reference when dispatched as a sub-agent for **Step 1: Project Survey** — the initial scan that maps out the project's modules, technology stack, and analysis priorities.

## Input

You will receive:
- The project root directory path
- Any user-specified scope hints (e.g., "focus on backend only")

## Process

### 1. Quick Scan (breadth-first)

Start with a fast, broad scan to understand project shape **before** diving deep:

1. **Top-level directory listing** — understand the monorepo / multi-project layout
2. **Package manifest files** — read `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `build.gradle`, `pom.xml`, `CMakeLists.txt`, etc.
3. **README / index docs** — read `README.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, `docs/` overview
4. **Config files** — check `tsconfig.json`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/`, `Makefile`

### 2. Identify Tech Stack

From the scanned files, extract:

| Dimension | What to Look For | Examples |
|-----------|-----------------|----------|
| **Language** | File extensions, compiler config | TypeScript, Go, Python, Rust, Java |
| **Framework** | Import patterns, config files | React, Next.js, Express, FastAPI, Gin, Spring Boot |
| **Database** | ORM config, connection strings | PostgreSQL, MongoDB, Redis, SQLite |
| **Message Queue** | Client libraries, config | Kafka, RabbitMQ, Redis pub/sub |
| **Testing** | Test directories, test frameworks | Jest, pytest, Go testing, JUnit |
| **Build System** | Build config files | Vite, Webpack, esbuild, Cargo, Maven |
| **Infrastructure** | Docker, K8s, CI configs | Docker, Kubernetes, GitHub Actions |
| **Monorepo Tool** | Workspace config | Turborepo, Nx, pnpm workspaces, Lerna |

### 3. Identify Modules

Group code into logical modules. Use these heuristics:

- **Monorepo packages**: `packages/`, `apps/`, `libs/` directories
- **Directory clusters**: subdirectories with internal cohesion (own `__init__`, own `mod.rs`, own `index.ts`)
- **Domain boundaries**: `auth/`, `billing/`, `search/`, `api/`, `core/`
- **Layer boundaries**: `domain/`, `infrastructure/`, `application/`, `presentation/`
- **Runtime boundaries**: separate binaries, services, or entry points

For each module, capture:
- Module name (kebab-case slug)
- Path relative to project root
- One-line purpose description
- Primary language
- Key dependencies (what other modules/systems it depends on)
- File count (approximate)

### 4. Identify Core Technical Highlights

Flag modules or areas that involve notable technical complexity:

- **Custom frameworks or DSLs** — does the project define its own runtime, compiler, or domain language?
- **Non-trivial state machines** — complex state transitions, workflow engines
- **Plugin / extension systems** — dynamic loading, hook systems, middleware chains
- **Custom algorithms** — domain-specific computation beyond CRUD
- **Cross-cutting concerns** — auth, logging, tracing, feature flags
- **Data pipelines** — ETL, stream processing, batch jobs
- **Protocol implementations** — custom RPC, WebSocket protocols, binary formats
- **Performance-critical paths** — caching layers, query optimization, connection pooling
- **Security-sensitive code** — auth flows, encryption, input sanitization

### 5. Prioritize Modules for Analysis

Assign each module a priority for Step 2 deep-dive:

| Priority | Criteria | Max Modules |
|----------|----------|-------------|
| **High** | Contains custom architecture, DSL, non-trivial algorithms, or novel patterns | All |
| **Medium** | Demonstrates solid engineering practices, clean boundaries, good testing | Up to 8 |
| **Low** | Boilerplate, config, generated code, simple CRUD wrappers | Skip |

## Output Contract

Save the result to `<output_dir>/project-overview.md`. The file MUST follow this exact structure:

```markdown
# Project Overview: <project-name>

## Summary

<2-3 sentences describing what the project does and its technical identity>

## Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Language | ... | ... |
| Framework | ... | ... |
| Database | ... | ... |
| ... | ... | ... |

## Module Map

| # | Module | Path | Description | Language | Key Dependencies | Files (~) | Priority |
|---|--------|------|-------------|----------|------------------|-----------|----------|
| 1 | <slug> | <path> | <one-line> | <lang> | <deps> | <N> | High/Medium/Low |
| 2 | ... | ... | ... | ... | ... | ... | ... |

## Core Technical Highlights

- **<highlight-1>**: <why it matters for learning — 1-2 sentences>
- **<highlight-2>**: <why it matters for learning — 1-2 sentences>
- ...

## Analysis Plan

<Brief note on which modules will be deep-dived in Step 2, grouped by priority>

**High priority** (<N> modules): <module slugs>
**Medium priority** (<N> modules): <module slugs>
**Low priority** (skipped): <module slugs or count>
```

## Key Rules

1. **Breadth before depth** — scan widely first, don't get lost in one file
2. **Read key files, not all files** — for module identification, read directory listings and index files; don't read every source file
3. **Flag what's interesting** — a module full of CRUD scaffolds is low priority regardless of size
4. **Estimate, don't count exactly** — approximate file counts are fine
5. **Write the output file** — use the Write tool to save to the specified output path; do not return the content inline
6. **Be concise** — the overview should be skimmable in under 2 minutes
