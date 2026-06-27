---
name: extra-knowledge
description: 'Extract design patterns, architecture decisions, and engineering insights worth learning from a codebase. Triggers when users ask to "analyze this codebase for learning", "extract knowledge from this project", "what can I learn from this repo", "find design patterns worth studying", "extra knowledge", or "codebase knowledge extraction". Use cases: studying open-source projects, onboarding to a new codebase, documenting tribal knowledge, creating learning notes from existing code.'
---

# Extra Knowledge Skill

## Overview

You will analyze a codebase to extract design patterns, architecture decisions, and engineering insights worth learning — producing structured documentation that helps developers understand not just *what* the code does, but *why* it's designed that way and *what they can learn* from it.

Core principle: **discover what's instructive, not just what's present** — skip boilerplate and standard framework usage; highlight designs, patterns, and trade-offs that a skilled developer would find worth studying. Each module report starts with an **IPO diagram** (Input-Process-Output table) and a **Mermaid flowchart** for quick visual orientation, followed by detailed analysis with **simplified code snippets** copied from the actual source — so readers see both the big picture and the concrete implementation.

## Core Responsibilities

1. Survey the project to map modules, technology stack, and core technical highlights.
2. Dispatch parallel sub-agents to deep-dive each module, extracting patterns and insights.
3. Synthesize findings into a structured, navigable knowledge base under `.Poseidon/extra-knowledge/`.

## Input Requirements

- **Primary input**: a path to the codebase to analyze (absolute or relative to workspace root)
- **Scope hints** (optional): the user may specify focus areas, e.g., "focus on backend services", "skip tests", "only analyze the core module"
- If no path is provided, default to the current workspace root (`/Users/xy/Project/skills/Poseidon`)
- The codebase must be on disk and readable — this skill does not fetch remote repositories

## Output Format

All output is written to `.Poseidon/extra-knowledge/` under the **target project's root**:

```
.Poseidon/extra-knowledge/
├── INDEX.md                  # Master index — links to all reports with one-line summaries
├── project-overview.md       # Step 1 output — tech stack, module map, analysis plan
└── modules/                  # Step 2 output — per-module deep-dive reports
    ├── <module-a>.md
    ├── <module-b>.md
    └── ...
```

## Reference Loading Rules

- For Step 1 sub-agent contract, load `references/project-survey-guide.md`
- For Step 2 sub-agent contract, load `references/module-analysis-guide.md`
- Load references **only** when dispatching the corresponding sub-agent — do not pre-load into your context

## Workflow

### Step 1: Project Survey

**Goal**: Build a module map and identify what's worth deep-diving.

1. **Confirm scope** with the user if the project path is ambiguous or the codebase is large (>200 source files). Ask:

   > I'll survey `<path>` to identify modules and technical highlights. Any areas I should focus on or skip?

2. **Dispatch a survey sub-agent** using the `Agent` tool with `subagent_type: "general-purpose"`:

   - **Prompt**: Instruct the sub-agent to survey the project per the contract in `references/project-survey-guide.md`. Include:
     - The project root path
     - Any user-specified scope hints
     - The output file path: `<project-root>/.Poseidon/extra-knowledge/project-overview.md`
     - A clear instruction: "Read the project-survey-guide.md reference below for your contract. Write your output to the specified file path using the Write tool. Do NOT return the content inline — write it to the file."

   - **Reference handling**: Copy the **full content** of `references/project-survey-guide.md` into the sub-agent prompt under a "## Reference: Project Survey Guide" heading, so the sub-agent can access it without accessing the file system.

   Use `run_in_background: false` — Step 2 depends on this output.

3. **Verify the output**: after the sub-agent completes, read the generated `project-overview.md` to confirm it contains:
   - A technology stack table
   - A module map with priorities
   - Core technical highlights

   If the output is incomplete, ask the sub-agent to fill gaps before proceeding.

### Step 2: Parallel Module Deep-Dive

**Goal**: Extract design patterns, technical decisions, and engineering insights from each high and medium priority module identified in Step 1.

1. **Read the survey output**: parse `project-overview.md` to extract:
   - The list of **high-priority modules** (all must be analyzed)
   - The list of **medium-priority modules** (analyze up to 6; skip if more)
   - For each module: name, path, language, and key technical highlights

2. **Dispatch parallel sub-agents** — one per module — using the `Agent` tool with `subagent_type: "general-purpose"`. Launch all in one message so they run concurrently.

   For each sub-agent, construct the prompt:

   - **Module identity**: module name, path, language, and technical highlights from the survey
   - **Contract**: copy the **full content** of `references/module-analysis-guide.md` under a "## Reference: Module Analysis Guide" heading
   - **Output path**: `<project-root>/.Poseidon/extra-knowledge/modules/<module-slug>.md`
   - **Instruction**: "Read the Module Analysis Guide below for your contract. Read the project overview at `<project-root>/.Poseidon/extra-knowledge/project-overview.md` for context. Analyze the module at `<module-path>` and write your report to `<output-path>` using the Write tool. Do NOT return the content inline."

   **Parallelism rules**:
   - Dispatch all high-priority module agents concurrently in one batch
   - Dispatch medium-priority agents concurrently in a second batch (or same batch if total ≤ 8)
   - Never dispatch more than 10 module agents at once — batch if needed

3. **Monitor completion**: wait for all sub-agents to finish. If any sub-agent fails or produces an empty report, re-dispatch it once with a more specific prompt.

### Step 3: Synthesize Index

**Goal**: Create a master index that ties all reports together.

1. Read all generated module reports from `.Poseidon/extra-knowledge/modules/`.
2. Write `INDEX.md` to `.Poseidon/extra-knowledge/INDEX.md` with this structure:

```markdown
# Extra Knowledge Index: <project-name>

> Generated: <date> | Tool: extra-knowledge skill

## Project Summary

<2-3 sentences from the project overview>

## Reports

### Project Overview
- **[project-overview.md](./project-overview.md)** — Technology stack, module map, core technical highlights

### Module Deep-Dives

| # | Module | Report | Priority | Key Patterns | Top Takeaway |
|---|--------|--------|----------|--------------|--------------|
| 1 | <name> | [<name>.md](./modules/<name>.md) | High | <pattern list> | <one-line> |
| 2 | ... | ... | ... | ... | ... |

## Learning Pathways

### By Pattern Type
- **Architecture Patterns**: <links to relevant module sections>
- **Design Patterns**: <links>
- **Error Handling**: <links>
- **Testing Strategies**: <links>
- **Performance**: <links>

### By Module
<Link to each module report with one-line summary>

## Quick Takeaways

<5-10 bullet points — the most valuable insights across all modules, actionable for any developer>
```

3. Tell the user the output is ready:

   > Knowledge extraction complete. Reports written to `.Poseidon/extra-knowledge/`. Start with [INDEX.md](.Poseidon/extra-knowledge/INDEX.md) for an overview, or jump directly to any module report under `.Poseidon/extra-knowledge/modules/`.

## Key Rules

1. **Survey before diving** — never skip Step 1; the module map prevents wasted analysis on boilerplate
2. **Parallelism is essential** — Step 2 module agents MUST run in parallel, not sequentially
3. **Sub-agents write files** — sub-agents use the Write tool to save reports; do NOT return inline content
4. **Reference contracts are self-contained** — copy the full reference content into each sub-agent prompt so they don't need filesystem access to the skill directory
5. **Quality over coverage** — it's better to deep-analyze 5 modules well than shallow-analyze 15
6. **Skip the obvious** — don't report "uses React hooks" or "has unit tests"; report *how* they use hooks in an instructive way
7. **Respect user scope** — if the user says "focus on auth module", only survey and analyze that module
8. **Handle large codebases** — if the project has >500 source files, ask the user to narrow scope before Step 1
9. **Verify before synthesizing** — check that Step 2 reports are non-empty before writing the index
10. **Use absolute paths** — always pass absolute paths to sub-agents for both source and output

## Edge Cases

- **No modules identified**: if Step 1 finds no analyzable modules (e.g., the project is a single script), skip Step 2 and write a single report directly
- **All modules low priority**: tell the user the project appears to be mostly boilerplate/CRUD and ask if they want to proceed anyway
- **Sub-agent timeout**: if a module agent times out, note it in the index under "Blind Spots" and continue with completed modules
- **Monorepo with 20+ packages**: ask the user to specify a subset (e.g., "just the api and core packages") before Step 1
- **Binary / generated files in module**: skip them; analyze only hand-written source code
- **Output directory exists from previous run**: ask the user whether to overwrite or merge before proceeding
- **No architecture docs found**: proceed with source-only analysis; note the gap in the overview
- **Module with 1-2 files**: still analyze if flagged as high priority; the small surface area may still contain instructive designs

## Limitations

- **Static analysis only** — cannot observe runtime behavior, performance characteristics, or live data flow
- **Requires readable source** — not useful for compiled/minified/obfuscated code or closed-source binaries
- **Not a replacement for reading the code** — reports are learning aids, not exhaustive documentation
- **Depends on sub-agent quality** — pattern recognition quality varies with model capability; complex or novel patterns may be missed
- **Language-agnostic but best-effort** — works with any language but analysis depth depends on the sub-agent's familiarity with the language's idioms
- **Does not modify the project** — read-only; all output goes to `.Poseidon/extra-knowledge/`
