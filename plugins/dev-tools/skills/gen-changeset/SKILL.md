---
name: gen-changeset
description: 'Generate changesets and release notes from actual code changes, following Changesets and Semantic Versioning. Triggers when users ask to "add a changeset", "create a changeset", "write a changelog entry", "generate release notes", "decide the version bump", "check changeset status", or say "生成 changeset"、"写 changeset"、"加变更说明"、"更新日志"、"发版说明"、"该升哪个版本". Detects the repo release tooling (Changesets, release-please, semantic-release, Lerna, git-cliff, Keep a Changelog), maps changed files to workspace packages, chooses major/minor/patch by public API impact, writes WHAT/WHY/HOW summaries with migration notes for breaking changes, and validates with a deterministic script plus `changeset status`. Never runs version/publish, edits package versions, or commits without explicit approval.'
---

# Gen Changeset Skill

## Overview

You will turn a set of code changes into release-ready changesets (or the equivalent changelog artifact for the repo's release tooling). Each artifact must answer three questions for a package consumer: **what changed, why it matters, and what they must do about it**.

Core principle: **the bump follows public impact, and the summary follows the consumer.** Diff size, effort, or commit count never decide the version. Detect the repo's release workflow before writing anything; Changesets is the primary target, not the only one.

Scope boundary: this skill owns release artifacts. For a reviewer-facing PR description use `pr`; for code findings use `code-review`.

## Core Responsibilities

1. Detect the release workflow and its configuration, conventions, and base branch.
2. Establish the change baseline (branch, PR, staged, or working tree) and map changed files to workspace packages.
3. Decide the semver bump per package from public API and behavior impact.
4. Write consumer-facing summaries with migration instructions for breaking changes.
5. Create or edit only the release artifact the repo's tooling actually consumes.
6. Validate against the workspace and the tooling, then report evidence and gaps.

## Input Requirements

- **Repo** (optional): path; default to the current working directory.
- **Change scope** (optional): branch diff, PR, staged, unstaged, or a user-described change. Infer from git state; ask only when several scopes are plausible.
- **Base ref** (optional): from `.changeset/config.json` `baseBranch`, else `main` / `master` merge-base.
- **Packages** (optional): limit to named packages; otherwise derive from changed files.
- **Bump override** (optional): the user may insist on a bump; record the disagreement and follow their decision.
- **Language** (optional): match existing changesets / `CHANGELOG.md`; fall back to the user's language.

If the diff is empty or the requested package does not exist, stop and report that instead of inventing a change.

## Output Format

**Primary (Changesets repos):** one or more files in `.changeset/`, e.g. `.changeset/add-csv-export.md`:

```markdown
---
"@acme/sdk": minor
"@acme/cli": patch
---

Added `exportCsv()` for exporting query results. The CLI exposes it as `acme export --format csv`.
```

**Fallbacks:** a `CHANGELOG.md` `Unreleased` entry (Keep a Changelog mode) or a conventional commit message for commit-driven tools. See `references/release-tools.md`.

**Plan before writing** when any of these is true — otherwise write directly and report:

- more than one package is affected, or
- a major bump is proposed, or
- the artifact edits an existing `CHANGELOG.md`, or
- the repo has no release tooling and setup is being discussed.

Plan format:

```md
| File | Package | Bump | Public impact (evidence) |
|------|---------|------|--------------------------|
| `packages/sdk` | `@acme/sdk` | minor | new exported `exportCsv()` in `src/index.ts` |
| `packages/cli` | `@acme/cli` | patch | new flag wired to the SDK, no behavior change |
```

## Reference Loading Rules

- Read `references/changesets-format.md` before writing any `.changeset` file; it owns the exact format, config keys, and CLI behavior.
- Read `references/bump-decision.md` whenever choosing a bump, especially for breaking changes, `0.x`, private packages, dependency-only changes, or fixed/linked groups.
- Read `references/summary-writing.md` before drafting summary text.
- Read `references/release-tools.md` when `.changeset/config.json` is absent or another release tool is detected.
- Run `scripts/changeset_lint.py` before delivery in Changesets mode.
- Load only the references the current step needs.

## Workflow

### Step 1: Detect the Release Workflow

```bash
git rev-parse --show-toplevel
ls .changeset/config.json release-please-config.json .release-please-manifest.json \
   .releaserc .releaserc.json .releaserc.js release.config.js lerna.json cliff.toml 2>/dev/null
```

Also inspect `package.json` for `workspaces`, release scripts, and the package manager lockfile.

| Signal | Mode |
|--------|------|
| `.changeset/config.json` | Changesets (primary) |
| `release-please-config.json` / `.release-please-manifest.json` | release-please — commit-driven |
| `.releaserc*` / `release.config.*` | semantic-release — commit-driven |
| `lerna.json` | Lerna version/changelog |
| `cliff.toml` | git-cliff — commit-driven |
| `CHANGELOG.md` only | Keep a Changelog fallback |
| None | Ask before scaffolding anything |

Never add a second release system. If the repo uses a commit-driven tool, do **not** create `.changeset` files; produce the commit message or changelog entry that tool consumes. Do not run `changeset init` unless the user explicitly asks to adopt Changesets.

### Step 2: Establish the Baseline and Changed Files

Read the config's `baseBranch` when present. Then collect the change set for the chosen scope:

```bash
git branch --show-current
git status --short
git diff --name-only "<base>...HEAD"        # committed branch changes
git diff --cached --name-only               # staged
git diff --name-only                        # unstaged
git merge-base "<base>" HEAD
```

Rules:

- Use the merge-base for branch comparisons; a plain `git diff <base>` includes unrelated upstream changes.
- Include untracked files when they are part of the change.
- Ignore `node_modules/`, `dist/`, `build/`, `vendor/`, coverage, and generated outputs.
- Lockfile-only changes usually need no changeset; a `package.json` dependency change may.
- For an explicit PR, prefer `gh pr diff --name-only <n>` or the diff the user provides.

### Step 3: Map Files to Packages

Read the workspace globs (`pnpm-workspace.yaml`, `package.json` `workspaces`, `lerna.json`) and each package's `package.json` (`name`, `version`, `private`).

- A file under a package directory belongs to that package.
- Root config/CI/docs/tests belong to no published package.
- A change to a private app that is not versioned needs no changeset.
- A change to a shared internal package affects consumers; bump the shared package, and bump a dependent only when the dependent's own published surface changes. Changesets updates internal dependency ranges during `version` according to `updateInternalDependencies`.
- If one PR contains several consumer-visible changes, prefer several changesets over one vague entry. Changesets stack.
- Check `.changeset/config.json` `changedFilePatterns` when deciding whether a file counts as a package change.

### Step 4: Choose the Bump

Apply `references/bump-decision.md`. The one-question test:

1. Would a correct consumer have to change code, config, or supported runtime? → **major**
2. Can they get new behavior by opting in, with existing code still valid? → **minor**
3. Is it a backward-compatible correction to intended behavior? → **patch**
4. Does nothing consumer-visible change? → **no release** (empty changeset only if CI blocks)

Record the evidence (file and symbol) for each decision. A breaking change requires migration instructions in the summary, not just a `major` keyword.

### Step 5: Draft the Summary

Follow `references/summary-writing.md`:

- **What** changed, named by public symbol, flag, config key, or behavior.
- **Why** it matters to a consumer, when that is not obvious.
- **How** to update, required for breaking changes; include a before/after snippet when renaming or changing signatures.

Keep patch summaries to one sentence, minor to one to three sentences, and major to a short explanation plus a migration block. Write in the repo's existing changeset language and tense.

### Step 6: Write the Artifact

For Changesets, write the file directly (do not drive the interactive `changeset add` prompt):

````markdown
---
"@acme/sdk": major
---

Renamed `fetchUsers()` to `listUsers()` and changed the return type from an array to `{ items, nextCursor }`.

To migrate:

```diff
- const users = await fetchUsers({ page });
+ const { items } = await listUsers({ cursor });
```
````

Rules:

- Quote package names; use the exact `name` from `package.json`.
- One logical consumer-visible change per file; split files when bumps or summaries differ.
- Multiple packages may share one file only when the same change and bump apply to all.
- Use a descriptive kebab-case filename (`add-csv-export.md`); rename only your own new files.
- Empty changeset: a file containing only `---\n---`, used solely when CI requires a changeset but nothing should release. Prefer `changeset add --empty` when the CLI is available.
- Never edit `package.json` versions, generated `CHANGELOG.md` files, or other pending changesets.

For non-Changesets modes, follow `references/release-tools.md` and edit only the file the tool owns.

### Step 7: Validate

Run the bundled linter from the target repository:

```bash
python3 "<skill-dir>/scripts/changeset_lint.py" --repo . --since "<base>"
```

It checks frontmatter syntax, bump values, workspace package names, summary quality, placeholder text, major-change migration guidance, empty changesets, and the config's ignored/private packages. Use `--all` to audit every pending changeset and `--strict` to fail on warnings.

Then, when the package manager and installed dependencies allow it, run the project's own check without installing anything:

```bash
pnpm changeset status --since "<base>"    # pnpm-lock.yaml
yarn changeset status --since "<base>"    # yarn.lock
npx --no-install @changesets/cli status --since "<base>"  # package-lock.json
bunx --no-install @changesets/cli status --since "<base>"
```

If the CLI is unavailable, say so; do not install packages or run `version` / `publish` to compensate. Re-read every written file and confirm package names, bumps, and migrations by eye.

### Step 8: Report

Report one row per artifact:

| Field | Value |
|-------|-------|
| File | `.changeset/add-csv-export.md` |
| Package(s) | `@acme/sdk` minor |
| Evidence | `src/csv.ts:12`, new export in `src/index.ts` |
| Validation | linter: clean; `changeset status`: pending 1 |
| Gaps | CLI not installed; status not run |

Also state what was intentionally omitted and why (docs-only, tests-only, private app) and any follow-up the user must decide (adopt Changesets, add an empty changeset, split a PR).

## Key Rules

1. **Detect first** — never assume Changesets or write a changeset into a release-please/semantic-release repo.
2. **Public impact decides the bump** — not diff size, effort, or commit count.
3. **Exact names only** — every package in the frontmatter must exist in the workspace.
4. **Major means migration** — a breaking bump without an update path is incomplete.
5. **Consumer-facing summaries** — no internal tickets as the only content, no "misc fixes".
6. **One logical change per changeset** — split when bump or message differs.
7. **Respect repo conventions** — language, tense, filename style, changelog generator, fixed/linked groups.
8. **Write only release artifacts** — no version edits, no `changeset version`, no `publish`, no git staging/commit/push unless the user explicitly asks.
9. **Validate before delivery** — a clean linter is necessary, not sufficient; check the diff reasoning too.
10. **Report honestly** — missing tooling and unverified claims are gaps, not silent assumptions.

## Edge Cases

- **No `.changeset` directory** — offer Changesets adoption or fall back to `CHANGELOG.md`; never scaffold release tooling unasked.
- **Private, unversioned package** — no changeset; check `private` and `privatePackages.version`.
- **Package in `ignore`** — a changeset naming it may block unrelated publishes; warn and exclude unless the user insists.
- **Fixed group** — all packages release the same version; bump the highest bump required. **Linked group** — packages share a version floor; the highest bump in the group wins.
- **`0.x` project** — Changesets applies `major` literally (`0.4.0 → 1.0.0`), while many teams treat pre-1.0 breaking changes as `minor` (`0.4.0 → 0.5.0`). Follow the project's documented policy; if none exists, ask before choosing, and state the assumption. A deliberate `1.0.0` graduation is a product decision.
- **Dependency-only change** — bump the package whose public dependency contract changes; a pure lockfile refresh is no release.
- **Pre-release mode** — `.changeset/pre.json` means the same bump rules apply to a pre-release channel; never run `pre enter/exit`.
- **Existing pending changeset for the same package** — add a separate logical entry or leave it alone; do not rewrite another author's file.
- **Docs/tests/CI only** — no release; explain the empty changeset option if CI blocks merges.
- **Renamed/deleted package** — remove stale frontmatter references; confirm the new name in the workspace before writing.
- **Multiple plausible bumps** — ask one batched question with major/minor/patch consequences; do not silently pick.
- **Non-npm artifact (Docker image, Go/Python package)** — Changesets can version it only when the package has a `package.json` with `name`, `version`, and `private`, and `privatePackages.version` is `true`; otherwise use the changelog fallback.
- **CI uses `changeset status --since main`** — align the base ref with CI to avoid a false pass.

## Limitations

- Cannot infer product intent or unpublished plans; bump choice remains a judgment call backed by evidence.
- Does not build, test, or run the code, so behavior claims rest on the diff, types, tests, and docs.
- The linter is static: it does not run the Changesets CLI, resolve dependency graphs, or execute release commands.
- Does not publish, version, tag, commit, or open release PRs.
- Requires a `package.json` per versioned package; projects without one fall back to changelog entries. Changesets is not a publishing tool for non-npm registries.
