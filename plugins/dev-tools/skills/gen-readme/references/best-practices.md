# README Best Practices

Research-backed patterns for a README that is useful on first contact and remains trustworthy as the project changes. This guide intentionally uses **positive examples only** — study what works, not a gallery of failures.

## 1. What a README Is For

A README answers five questions in the reader's order of need:

1. **What is this?** — name plus one-sentence description.
2. **Why should I care?** — the problem it solves and the one differentiator.
3. **How do I start?** — installation and the smallest working example.
4. **Where do I go next?** — docs, API reference, examples, support.
5. **Who owns it?** — maintainers, contribution path, license.

Sources converge on the same contract:

- GitHub describes the README as the first thing visitors see: what the project does, why it is useful, how to get started, where to get help, and who maintains it. It should contain only what developers need to start using and contributing; longer material belongs in a wiki.
- `makeareadme.com` recommends title, description, installation, usage, contributing, and license, with optional badges, visuals, support, and roadmap.
- The `standard-readme` specification fixes a section order (title → description → TOC → install → usage → API → maintainers → contributing → license) and treats install/usage as required for functional repositories.
- Readme Driven Development argues for writing the README first: it forces the public API and intended organization to be designed before code makes changes expensive, and it serves as an interface contract for teammates.

**Practical rule:** the README is an entry point plus a contract. It is not the manual, the changelog, or the marketing site.

## 2. The First Screen

Most readers decide in the first screen. A strong first screen contains, roughly in this order:

1. **Title** — matches the repository/package name.
2. **Pitch** — one sentence, ideally under 120 characters, stating what it is, who it is for, and why it is different.
3. **Proof** — a screenshot, demo GIF, or realistic terminal transcript. Show the result before explaining it.
4. **Fastest path** — install or quick-start command visible without scrolling.
5. **Status callout** — only when needed: alpha, experimental, deprecated, or requires access.

Positive patterns to borrow:

- **uv** opens with title, badges, a one-line tagline, and a benchmark visual, then shows a copy-paste install command before explaining features.
- **ollama** opens with a hero logo and tagline, then puts platform-specific download commands first, each with an "or" fallback.
- **fzf** opens with a centered logo/badge block, a one-line pitch, a screenshot, and a four-bullet highlights list.

## 3. Section Priority Ladder

| Priority | Sections | Notes |
|----------|----------|-------|
| **Core** | Title, short description, install/quick start, usage, license | Required for functional projects |
| **Core for public projects** | Contributing, support/where to get help | State whether contributions are accepted |
| **Style-specific** | API, CLI reference, configuration, architecture, deployment, operations, package map | Load the matching template |
| **Useful optional** | TOC, badges, features/highlights, screenshots, compatibility, FAQ, troubleshooting, roadmap, acknowledgments | Include only when they add information |

Per `standard-readme`, section order matters: readers expect installation before deep usage, API before maintainers, and license last.

## 4. Proven Patterns

### 4.1 Fastest Path First

Lead with the one command that works for most readers. Put alternative package managers and platforms after it, clearly labeled. `ollama` does this with one-line commands per platform and a manual alternative; `uv` presents the standalone installer first and PyPI options second.

**Why it works:** a newcomer can act after reading one line, while power users can still find their preferred channel.

### 4.2 Show Real Output

Pair commands with a short, realistic transcript. `uv` shows `$ uv add ruff` followed by resolver output; `fzf` starts usage with the minimal `find * -type f | fzf > selected` pipeline and then layers complexity.

**Why it works:** output proves the command works and sets expectations, which reduces support questions.

### 4.3 Progressive Disclosure

Use a consistent three-beat structure for each capability:

1. One sentence on what it does.
2. A small runnable example or transcript.
3. A link to the full guide.

`uv` repeats this pattern across Projects, Scripts, Tools, Python versions, and the pip interface. `fzf` moves from install → usage → examples → advanced topics.

**Why it works:** the README stays scannable while detail lives where it can be maintained.

### 4.4 Consistent Micro-Structure

Repeated blocks should look the same. `uv` feature subsections all follow description → example → link. `ollama` integration entries all follow `Name – description`.

**Why it works:** once a reader learns one block, every later block is predictable to skim.

### 4.5 Restrained, Truthful Badges

Badges are optional. `standard-readme` suggests shields.io or similar, prefers locally hosted static badges, and warns against excess. `awesome-readme` highlights READMEs whose badges communicate build, version, coverage, or license status.

**Rules:**

- Every badge must have a live source and a meaningful link.
- Prefer 3–5 badges: CI, package version, supported runtime, license.
- Do not use badges for vanity metrics or numbers that will go stale.
- Do not leak private metadata in public badges for internal repositories.

### 4.6 Visual Proof

A screenshot or GIF is often the fastest explanation. `fzf` uses a terminal screenshot; `ollama` uses a hero visual; `Abblix/Oidc.Server` and `doomemacs` are cited by `awesome-readme` for banner/visual hierarchy and centered, well-organized headers.

**Rules:**

- Use a real image from the repo; never reference a missing file.
- Keep alt text descriptive and stable.
- Put large media in `docs/assets/` or `assets/` and link relatively.

### 4.7 Orientation for Long READMEs

`standard-readme` requires a table of contents unless the README is under 100 lines. GitHub automatically generates an outline and linkable heading anchors for rendered Markdown, but an explicit TOC still helps readers arriving from a clone or a non-GitHub host.

**Rules:**

- Add a TOC around 100 lines or when there are more than 5 level-two sections.
- Keep TOC entries in the same order as the document.
- Validate anchors after renaming headings.

### 4.8 Verifiable Claims

Performance, compatibility, and security claims need evidence or a link to evidence. `uv` pairs its speed claim with a benchmark link. CI badges and version support tables are useful only when they reflect reality.

**Rules:**

- No invented numbers, benchmarks, or user counts.
- Link the source of any comparative claim.
- Date or version-gate claims that can drift.

### 4.9 Link Out Instead of Duplicating

GitHub's guidance is explicit: keep the README to what developers need to start; move longer documentation elsewhere. `uv` and `fzf` both route readers to dedicated guides for depth.

**Rules:**

- One short example per capability is enough.
- Link to `docs/`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, and API references.
- Avoid copying docs that will drift out of sync.

### 4.10 Operational Clarity for Internal Services

For internal services, the README is the first page of the runbook. Strong internal READMEs add:

- Owner, team channel, on-call rotation, and service tier.
- Architecture diagram and upstream/downstream dependencies.
- Local development in three commands or fewer.
- Configuration **names** and safe defaults — never secret values.
- Links to dashboards, alerts, logs, deploy pipeline, and runbooks.
- Data sensitivity and access requirements.

This pattern extends the README contract from "how do I run it?" to "how do I operate it safely?"

### 4.11 Monorepo and Package READMEs

A monorepo usually needs more than one README, and the files serve different readers:

- **Root README** — what the repo is, the package map (`apps/` vs `packages/`), the shared quick start, and how to contribute. It navigates; it does not duplicate package detail.
- **Package README** — self-contained documentation for that package: name, install command, public surface (`exports` / `bin` / `main`), usage, compatibility, and license. A reader may arrive directly from npm or a directory view.
- **Scope is a product decision** — say explicitly whether package READMEs are included. Silently skipping them leaves published packages with missing or stale documentation.

Why package READMEs matter:

- npm requires the file to be named `README.md` in the package root; it is always included in the published package regardless of the `files` field, and npm renders it on the package page. Edits appear only after publishing a new version.
- Turborepo's structure guidance separates `apps/` (applications and services) from `packages/` (libraries and tooling); each package owns its `package.json`, name, scripts, and exports. That is also the natural boundary for per-package READMEs.
- pnpm workspaces declare package locations in `pnpm-workspace.yaml`; that file is the reliable inventory for which directories need docs.

Practical rules:

- Use the `monorepo` template for the root; use `library`, `cli`, `app`, or `internal-service` for each package based on its own surface.
- Include a package table in the root with a link to every in-scope package README.
- Keep package READMEs standalone; do not rely on the root README for install or API context.
- Exclude vendored, fixture, and generated READMEs unless they are part of the delivered surface.

### 4.12 Optional Enrichment

Beyond the core sections, a README can use optional elements: banners/logos, tech-stack icons, demo videos, charts/benchmarks, star history, security policy, citation, contributors, sponsors, roadmap, changelog, support, TOC, background, maintainers, and code of conduct. They are not required and should never replace the core path.

Select them by information value, not decoration:

- A banner or icon row should help recognition, not push the install command below the fold.
- A chart or star history should link its data and date; it is not proof by itself.
- Community blocks (contributors, sponsors, roadmap) must be current and consented.
- Every image needs alt text, reasonable weight, and the right license.

See `references/optional-elements.md` for the full catalog, module IDs, snippets, and asset rules.

## 5. Length, Formatting, and Maintenance

- **Length:** `makeareadme.com` notes a README can be too long, but "too long is better than too short"; GitHub recommends moving depth to a wiki. The practical target is one screen for the quick path plus linked depth.
- **Truncation:** GitHub truncates rendered content beyond 500 KiB. Move large tables, logs, and generated references out.
- **Formatting:** short paragraphs, one idea per bullet, fenced code with a language hint, and relative links for repository files.
- **Maintenance:** treat README commands and links as code. Re-check them when manifests, CI, or entry points change. Stale quick starts are worse than none.
- **Language:** when multiple languages exist and English is one of them, `README.md` holds English and `README.<bcp47>.md` holds each translation (`README.zh-CN.md`). If English is not maintained, `README.md` holds the primary language and variants use BCP 47 suffixes. Keep section order aligned and link variants at the top.

## 6. What "Positive Examples Only" Means in Practice

- Describe the successful move and why it works.
- Quote short fragments only; do not reproduce entire READMEs.
- Prefer patterns that are observable in the linked repository today.
- Do not build a "bad README hall of shame." When a draft has a problem, describe the fix positively: what to include instead.

## 7. Sources

All sources accessed 2026-11-25.

| Source | URL | Takeaway |
|--------|-----|----------|
| Make a README | https://www.makeareadme.com/ | Section checklist; installation/usage for newcomers; longer is better than missing, but move detail out |
| Standard Readme spec | https://github.com/RichardLitt/standard-readme/blob/main/spec.md | Required order; short description <120 chars; TOC unless <100 lines; license last |
| GitHub: About READMEs | https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes | First thing visitors see; keep to getting started; 500 KiB truncation; relative links |
| Awesome README | https://github.com/matiassingers/awesome-readme | Visuals, clear description, navigation, badges, install/usage, contribution/license |
| freeCodeCamp: How to write a good README | https://www.freecodecamp.org/news/how-to-write-a-good-readme-file/ | What/why/how; step-by-step install; keep it updated; license |
| Readme Driven Development | https://tom.preston-werner.com/2010/08/23/readme-driven-development.html | README as design contract and public API definition |
| uv README | https://github.com/astral-sh/uv | Tagline + visual + fastest install + consistent feature blocks |
| fzf README | https://github.com/junegunn/fzf | Centered hero, screenshot, highlights, TOC, progressive usage |
| ollama README | https://github.com/ollama/ollama | Platform-first download commands, use-case sections, uniform integration list |
| npm: About package README files | https://docs.npmjs.com/about-package-readme-files | README.md in package root; rendered on npm; included on publish |
| npm: package.json | https://docs.npmjs.com/cli/v10/configuring-npm/package-json | README always included regardless of `files`; package metadata |
| Turborepo: Structuring a repository | https://turborepo.dev/docs/crafting-your-repository/structuring-a-repository | `apps/` vs `packages/`; each package owns its manifest and exports |
| pnpm: Workspaces | https://pnpm.io/workspaces | `pnpm-workspace.yaml` declares package locations |
