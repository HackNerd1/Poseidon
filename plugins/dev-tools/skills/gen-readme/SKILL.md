---
name: gen-readme
description: 'Generate, rewrite, or audit one or more READMEs from verified repository facts using selectable style templates, section modules, and optional visual/community elements. Triggers when users ask to "write a README", "generate README", "improve README", "rewrite README", "audit README", "add README banner", "add badges or icons", "add charts to README", "create project documentation", or say "写 README"、"生成 README"、"完善 README"、"README 优化"、"README 审查"、"给 README 加 banner"、"加徽章/图标"、"加图表". Use cases: new project README, open-source launch, internal service entry page, monorepo root and package READMEs, bilingual README, optional banner/tech icons/charts/contributors. Inventories workspace packages, presents a scope/style/module plan, waits for approval before replacing content or writing multiple files, then writes and audits each README with a deterministic script. Reports audit results and evidence gaps.'
---

# Gen README Skill

## Overview

You will create or improve one or more README files that take a newcomer from "what is this?" to "it runs" in the shortest reliable path. Ground every command, path, badge, and claim in the actual repository.

Core principle: **the README is a verified entry point, not marketing copy.** Prefer repo evidence over assumptions, show working examples over adjectives, and link to deeper docs instead of duplicating them. Use only positive, proven patterns — no anti-pattern galleries.

## Core Responsibilities

1. Determine mode, scope, and target files — including monorepo package READMEs when in scope.
2. Inventory the repository and build a per-file evidence map for every factual claim.
3. Select a style and core section modules for each target file.
4. Offer optional visual/community modules only when they add information.
5. Present the plan and wait for approval when replacing content or touching multiple files.
6. Draft, audit, write, and report — without silently changing the approved scope.

## Input Requirements

- **Target repo** (optional): path to the project; default to the current working directory.
- **Mode** (optional): `create`, `rewrite`, `update`, or `audit`; infer from whether a README exists and from user intent.
- **Scope** (optional): `root`, `packages`, or `all`. For monorepos, default to `root` only after telling the user which package READMEs are being skipped; ask before writing package READMEs.
- **Style** (optional): `library`, `cli`, `app`, `monorepo`, or `internal-service`; infer per file from repo signals.
- **Sections** (optional): module IDs from `references/modules.md` (for example `M1,M5,M6,M17`) to include, replace, or omit.
- **Extras** (optional): optional module IDs from `references/optional-elements.md` (for example `M21` banner, `M22` tech icons, `M24` charts, `M28` contributors).
- **Language** (optional): match the repo's existing documentation language by default.
- **Audience** (optional): public users, contributors, or internal engineers.

If the repo path is missing or points to an empty directory, ask before continuing.

## Output Format

Primary output: one or more README files at the approved paths (usually the repo root and/or package roots).

Before drafting, present one plan table for all target files:

```md
## README Plan

| File | Style | Action | Sections (M-IDs) | Notes |
|------|-------|--------|------------------|-------|
| `README.md` | monorepo | update | M1, M4–M5, M8–M9, M16–M17, M19 | drop roadmap |
| `packages/ui/README.md` | library | update | M1, M5–M6, M17 | published package |

**Repo:** <path> — <one-line what it is>
**Scope:** <root | packages | all> — <why>
**Language:** <language> — <existing docs language or user choice>
**Evidence:** <3-8 key facts with source files>
**Gaps:** <missing screenshots, license, commands that cannot be verified>
```

State which modules you dropped and why. For audit-only runs, report findings with file:line and the script summary; do not edit files.

## Reference Loading Rules

- **Always** read `references/best-practices.md` before drafting.
- Read `references/style-catalog.md` when choosing or confirming style.
- Read one template per target file from `references/templates/`:
  - `library.md`, `cli.md`, `app.md`, `monorepo.md`, `internal-service.md`
- Read `references/modules.md` when selecting core sections or swapping implementations.
- Read `references/optional-elements.md` when the user asks for banners, icons, charts, badges, contributors, sponsors, roadmap, or "what else can I add"; load only the chosen optional modules.
- Read `references/quality-checklist.md` before final delivery.
- Run `scripts/readme_audit.py` after drafting and after fixes.
- Load only what the current step needs.

**Template vs module contract:** the template defines the required sections and their order; modules are implementations of individual sections. You may replace a module implementation or add/remove optional sections, but do not remove a style's required sections without stating why in the plan.

## Workflow

### Step 1: Determine Mode, Scope, and Files

1. Confirm the repo root (`git rev-parse --show-toplevel` or the user's path).
2. Inventory README files and workspace packages:
   ```bash
   find . \( -name node_modules -o -name .git -o -name dist -o -name build -o -name .next -o -name vendor \) -prune -o -iname 'README*' -print
   ```
   Also inspect workspace manifests: root `package.json` `workspaces`, `pnpm-workspace.yaml`, `turbo.json` / `nx.json`, `Cargo.toml` `[workspace]`, `go.work`.
3. Build a target table before choosing mode:

   | Target | Package | Published? | Existing README | Proposed action |
   |--------|---------|------------|-----------------|-----------------|
   | `packages/ui` | `@acme/ui` | yes | yes | update |
   | `apps/showcase` | private app | no | yes | skip |

   For publishability, check `private`, `name`, `files`, and the package's own `README.md`. npm publishes a package-root README and renders it on the package page.
4. Resolve scope:
   - Single-package repo → `root`.
   - Monorepo and user says only "调整 README" → default `root`, explicitly say package READMEs are out of scope, and ask whether to include them before writing anything.
   - Monorepo and scope is ambiguous → ask: root only, published packages only, or all package READMEs.
5. Choose mode per file:
   - No README → `create`.
   - README exists and user asks to rewrite/replace → `rewrite`.
   - README exists and user asks to improve/fix → `update`.
   - User asks only to evaluate → `audit`.
   - Out of scope → `skip`; list skipped files in the plan.
6. If a README exists and mode is ambiguous, ask before proceeding.

Never overwrite an existing README without explicit approval of the plan.

**Audit-only fast path:** when the user only wants an assessment, skip drafting. Infer the closest style per file, run the audit script, load `references/quality-checklist.md`, and report findings grouped by gate with file:line and a concrete fix. Do not edit files unless the user asks.

### Step 2: Build the Evidence Map

Read each target's repo context before writing. The goal is a table of facts, each with a source file.

Collect, using read-only commands:

| Fact | Where to look |
|------|---------------|
| Project / package name | `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, plugin manifests |
| One-line purpose | repo description, top-level docs, source entry points |
| Install command | lockfiles + manifest (`package-lock.json` → `npm ci`; `pnpm-lock.yaml` → `pnpm install`; `yarn.lock` → `yarn`; `bun.lockb`/`bun.lock` → `bun install`; `uv.lock` → `uv sync`; `poetry.lock` → `poetry install`; `Cargo.lock` → `cargo build`) |
| Run / dev command | manifest `scripts`, `Makefile`, `justfile`, `Taskfile`, Docker Compose |
| Test / lint command | manifest scripts, CI workflows (`.github/workflows/`, `.gitlab-ci.yml`) |
| Public API / CLI entry | manifest `bin`, `main`, `exports`, CLI framework files, `cmd/` |
| Config surface | `.env.example`, config modules, CLI `--help`, docs |
| License | `LICENSE`, manifest `license` field |
| Repo URL | `git remote get-url origin` |
| Visuals | `docs/`, `assets/`, `images/`, existing README media |
| Existing docs | `docs/`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, `CHANGELOG.md` |
| Workspace context | root package list, package dependencies, package README status |
| Primary language | existing docs and comments |

Rules:

- Every install/run/test command in the README must trace to a manifest, Makefile, CI file, or verified `--help` output.
- If a command cannot be verified, omit it or mark it as a gap in the plan — do not invent one.
- Never copy secrets, private URLs, or personal data from config files.
- Read the full existing README before proposing changes; preserve unique, accurate content.
- For package READMEs, record whether the package is published and what `exports` / `bin` / `main` expose.

### Step 3: Select Style and Language per File

1. Read `references/style-catalog.md`.
2. Score each target's signals and recommend a style:
   - Root of a monorepo → `monorepo`.
   - Published package or SDK → `library`.
   - Executable package → `cli`.
   - Deployed application → `app`.
   - Private team service → `internal-service`.
3. State the reason in the plan. If two styles are genuinely plausible for a file, present the finalists and ask; keep the question to at most four options.
4. Choose language per file:
   - Existing README or docs language wins.
   - No signal → ask, or default to the language the user is using in conversation.
   - Bilingual → if English is one of the languages, `README.md` holds English and `README.<bcp47>.md` holds each translation (for example `README.zh-CN.md`); otherwise `README.md` holds the primary language and variants use BCP 47 suffixes. Add visible language links at the top of every variant.
   - When writing in a non-English language, translate the template's section titles and prose; keep code identifiers, commands, and file paths unchanged.
5. Choose length per file:
   - **One-screen** (roughly ≤120 lines): small libraries, early projects, internal tools.
   - **Full guide**: CLI tools, apps, monorepos, services with operations content.
   - Long content belongs in linked docs, not the README.

### Step 3.5: Offer Optional Enhancements (Only When Useful)

Core READMEs do not need extras. Load `references/optional-elements.md` when:

- the user asks for a banner, logo, tech-stack icons, charts, contributors, sponsors, roadmap, or other extras, or
- a public README would clearly benefit from a proof visual or credibility block.

Present a short menu grouped **Visual / Credibility / Community / Navigation**, recommend 2–4 modules for this style and audience, and let the user choose. Default to none. Do not add an optional module to the plan until the user selects it.

### Step 4: Build the Outline with Module IDs

1. Load one template per target file.
2. Map the template's sections to module IDs from `references/modules.md`; add chosen extras from `references/optional-elements.md`. Use a section name directly when no module exists (for example `Release workflow`).
3. For each file, mark sections keep / revise / add / remove:
   - `update` → mark existing sections to keep or revise.
   - `rewrite` → carry over accurate, uniquely useful blocks before replacing.
   - `create` → choose the default module set for the style.
4. Drop sections with no real content; do not ship empty headings. Record dropped modules in the plan's Notes.
5. Order by reader path: identity → value → fastest start → core usage → deeper usage → operations / community → license.

### Step 4.5: Confirm the Plan

Before drafting, present the plan table and wait for approval when:

- any target file already exists (`rewrite` or `update`), or
- the scope includes more than one file.

For a single new file (`create` with no existing README), show the plan and proceed unless the user asked to review it first. If the user asks to see the plan first, wait in every mode.

Approval must cover **scope, target files, style, and section/module list**. A request to "改善一下 README" is not approval of a plan you have not shown. If the user changes scope or modules mid-draft, return to Step 4 and re-confirm.

### Step 5: Draft the READMEs

Write each file using its approved template and modules.

Non-negotiable patterns:

1. **First screen earns the scroll** — title, ≤120-character pitch, one proof point (visual, demo, or terminal transcript), and the fastest install/start path.
2. **Show working output** — pair commands with realistic expected output; keep transcripts short.
3. **Fastest path first** — one default command, then alternatives labeled as alternatives.
4. **Progressive disclosure** — one-sentence explanation → small example → link to full docs.
5. **Consistent micro-structure** — repeated subsections use the same shape (description, command, output, link).
6. **Restrained badges** — only badges with a live, meaningful source; prefer static shields; do not badge vanity metrics.
7. **Trustworthy links** — relative links for repo files; absolute links only for external docs.
8. **License last** — correct license name and owner; never invent a license.
9. **No placeholders in the final file** — resolve `<...>`, `TODO`, and sample values; if a screenshot is unavailable, omit it and list it as a delivery gap.
10. **Match the repo's language and tone** — no translated-sounding filler; keep code identifiers in English.

For package READMEs, make the file self-contained: package name, install command, public surface, usage, and license/compatibility. Do not assume the reader arrived from the root README.

### Step 6: Audit and Fix

Run the audit from the target repository, resolving the script path relative to this `SKILL.md`. The script accepts one or more paths:

```bash
python3 "<skill-dir>/scripts/readme_audit.py" README.md --repo . --style monorepo
python3 "<skill-dir>/scripts/readme_audit.py" packages/*/README.md --repo . --style library
```

Repeat the command per style when package types differ (for example libraries vs apps). Multiple paths share one `--style`.

Then read `references/quality-checklist.md` and verify the human-judgment items:

- Can a newcomer reach a running state with the documented commands?
- Is every claim traceable to a file or verified command?
- Are all local links, images, and anchors valid?
- Does the README avoid duplicating docs it could link to?
- Is the tone appropriate for the audience (public vs internal)?
- Are optional images/icons/charts licensed, compressed, alt-texted, and linked to their source?
- For monorepos: does every in-scope package have a README, and does the root package table match the workspace?

Fix every error. Fix or explicitly justify every warning. Re-run the audit until clean or only justified warnings remain. The script exits `1` when errors remain (or when `--strict` is set and warnings remain), `2` when a README cannot be found.

### Step 7: Write and Report

1. Write only the files in the approved plan. If a file needs to be added, removed, or re-scoped, pause and re-confirm.
2. For bilingual READMEs, add the language switcher to both files in the same pass; keep section order aligned.
3. Compare the final content against the approved outline. Re-confirm only when the structure or scope changed materially.
4. Report per file:
   - Path, style, action
   - Section/module map
   - Audit summary (errors / warnings)
   - Evidence sources and gaps (screenshots, license, unverifiable commands)
   - Optional assets used or missing (banner, icons, charts, demo, contributor image)
   - Files skipped and why

## Key Rules

1. **Plan before write** — show scope, files, styles, and modules; get approval when replacing or touching multiple files.
2. **Scope is explicit** — never silently include or omit package READMEs in a monorepo.
3. **Repo evidence over invention** — commands, paths, versions, and badges must be verifiable.
4. **Template is the contract, modules are implementations** — swap implementations freely; keep required sections unless the plan says why.
5. **One style per file** — hybrid content stays subordinate to that file's primary reader path.
6. **First screen first** — identity, value, and quick start before depth.
7. **Show, don't tell** — examples and output beat adjectives.
8. **Link, don't duplicate** — the README is the entry point, not the manual.
9. **Optional means optional** — add banners, icons, charts, and community blocks only when they carry information and the user approved them.
10. **Positive patterns only** — use proven successful structures; do not include bad-example galleries.
11. **Copy-paste ready** — one command per step, correct fences and language hints.
12. **Respect existing work** — never discard accurate content during a rewrite.
13. **No fabricated visuals** — omit or mark gaps; never reference images that do not exist.
14. **Audit before delivery** — script errors block delivery; warnings need a decision.
15. **No secrets** — config examples use placeholders and names only.

## Edge Cases

- **README exists but is mostly good** — prefer `update`; rewrite only when structure is fundamentally wrong.
- **Monorepo** — the root README navigates; each in-scope package README is a separate deliverable with its own style. Package detail belongs in the package README, not the root.
- **Published package** — npm includes and renders a package-root README regardless of `files`; the package README must stand alone.
- **Private / unlicensed package** — state the internal or proprietary notice; do not link a missing `LICENSE`.
- **No CONTRIBUTING.md** — omit the contributing section or link the team's real process; do not fabricate a link.
- **Vendored / fixture READMEs** — exclude `vendor/`, `third_party/`, and test fixtures unless the user explicitly includes them.
- **No package manifest** — infer entry points from source and docs; mark unverifiable commands as gaps.
- **Library + CLI** — lead with the library API, add a CLI section after usage; ask if both audiences are first-class.
- **Internal/private service** — use the internal-service template; include ownership, access, configuration names, runbooks, and data sensitivity; avoid public badges that leak private metadata.
- **No license file** — omit the license section or state "No license declared"; recommend adding one; never guess.
- **Screenshots or banner assets unavailable** — omit the visual block, list capture suggestions in the delivery report; never hotlink an unlicensed or missing asset.
- **External chart/badge service unavailable** — keep a text fallback or a static badge; dynamic stats are optional, not the only proof.
- **Docs-only repository** — install/usage may be optional; lead with navigation and reading paths.
- **README over 500 KiB** — GitHub truncates the rendered view; move detail to linked docs.
- **Existing README in another language** — preserve it; add a variant only when the user wants bilingual docs.
- **Unfamiliar tech stack** — search the web only to confirm conventions; repo evidence still wins.

## Limitations

- Does not create screenshots, GIFs, logos, or benchmark data; it plans and places them.
- Cannot verify external URLs offline; the audit script checks local links and anchors only.
- Does not replace a full documentation site, API reference, or CONTRIBUTING guide.
- Does not execute install/deploy commands; command verification is static and traceable to manifests.
