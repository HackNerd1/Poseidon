# Changesets Format and Workflow

Facts below come from the Changesets documentation (writing changesets, config, CLI, automation, FAQ) plus Semantic Versioning. Prefer them over guesses; when a repo's config differs, the config wins.

## 1. What a Changeset Is

A changeset is a Markdown file in `.changeset/` with YAML frontmatter. The frontmatter lists packages and their semver bump types; the body is the changelog summary. It is committed with the code and consumed later by `changeset version`, which updates versions, internal dependency ranges, and `CHANGELOG.md`, then deletes the applied change sets.

```markdown
---
"@acme/sdk": minor
"@acme/cli": patch
---

Added `exportCsv()` for exporting query results. The CLI exposes it as `acme export --format csv`.
```

Rules:

- Package keys are the exact `name` values from each `package.json`.
- Bump values are exactly `major`, `minor`, or `patch`.
- Quote package names; unquoted scoped names (`@scope/pkg`) are invalid YAML because `@` cannot start a plain scalar.
- The body is Markdown; fenced code blocks and lists are allowed.
- Frontmatter may carry `_` override metadata for `@changesets/changelog-github` (`pr`, `author`, `commit`); leave it alone unless the repo uses it.

## 2. Empty Changesets

When CI blocks merges without a changeset but a change should not release anything, add an empty changeset: a file whose content is only the two delimiters.

```markdown
---
---
```

`changeset add --empty` creates one. Use it only for changes that genuinely need no release (tests, CI, docs outside published packages). Do not use it to avoid deciding a bump.

## 3. Naming and Grouping

- The CLI generates random human-readable names (`brave-lions-sing.md`); renaming is safe and descriptive kebab-case names are easier to review.
- Multiple changesets per PR are supported and encouraged when they describe different releases or different consumer-visible changes.
- A changeset is consumed once and deleted by `version`; `.changeset/` is not a notes folder.
- A changeset naming only skipped packages (unversioned private packages or `ignore` entries) stays in the folder because nothing was released.

## 4. Configuration (`.changeset/config.json`)

Default config:

```json
{
  "changelog": "@changesets/cli/changelog",
  "commit": false,
  "fixed": [],
  "linked": [],
  "access": "restricted",
  "baseBranch": "main",
  "changedFilePatterns": ["**"],
  "format": "auto",
  "privatePackages": { "version": false, "tag": false },
  "updateInternalDependencies": "patch",
  "ignore": [],
  "bumpVersionsWithWorkspaceProtocolOnly": false
}
```

Keys that change what you write:

| Key | Effect on changeset authoring |
|-----|-------------------------------|
| `baseBranch` | The ref for "what changed"; align `--since` with it. |
| `changedFilePatterns` | Picomatch patterns (relative to each package) that count as package changes. Tests-only edits may not count. |
| `fixed` | Groups that always share one version; bump the highest bump needed across the group. |
| `linked` | Groups that share a version floor; the highest bump in the group wins. |
| `ignore` | Packages excluded from releases; naming a mixed set can fail `version`. |
| `privatePackages` | Whether private packages are versioned/tagged; default is no version, no tag. |
| `updateInternalDependencies` | How internal dependency ranges are bumped (`patch` by default) when a dependency changes. |
| `access` | Publish visibility; do not change it while writing a changeset. |
| `changelog` | Generator; default adds commit links, `@changesets/changelog-github` adds PR/author, `false` disables changelogs. |

## 5. CLI Commands

| Command | Purpose |
|---------|---------|
| `changeset init` | One-time `.changeset` setup (interactive). Do not run unasked. |
| `changeset` / `changeset add` | Interactive add; detects changed packages since `baseBranch`. |
| `changeset add --empty` | Create an empty changeset. |
| `changeset add --since <ref>` | Suggest packages changed since another ref. |
| `changeset status --since <ref>` | Show pending releases; exits `1` when packages changed but no changesets exist. |
| `changeset status --output <file>` | Write status JSON for tooling. |
| `changeset version` | Consume changesets: bump versions, update dependents, write changelogs, delete applied files. |
| `changeset version --snapshot <tag>` | Snapshot release versions for testing. |
| `changeset publish` | Publish bumped packages and create tags (`pkg@x.y.z`, or `vx.y.z` for single-package repos). |
| `changeset pre enter <tag>` / `pre exit` | Enter/leave pre-release mode. Never run from this skill. |
| `changeset git-tag` | Create tags without publishing. |

Run via the repo's package manager: `pnpm changeset`, `yarn changeset`, `npx @changesets/cli`, or `bunx @changesets/cli`.

`changeset status` fails mid-`version`/`publish`; run it before those commands.

## 6. Monorepo Semantics

- `add` suggests packages changed since `baseBranch`, filtered by `changedFilePatterns`.
- A changeset may list several packages with different bumps.
- During `version`, internal dependency ranges are updated; dependents may receive a bump according to `updateInternalDependencies`.
- `fixed` guarantees identical versions; `linked` only shares the version floor. Both are config concerns — do not simulate them by hand-adding packages to a changeset.
- Do not bump a dependent merely because a dependency changed. Bump it when its own published surface or required peer range changes.

## 7. CI Practices

Changesets documentation recommends:

- **Non-blocking:** the Changesets GitHub Bot comments when a PR lacks a changeset. Preferred because not every change needs a release.
- **Blocking:** `changeset status --since <base>` in CI. It exits `1` only when there are changed packages and no new changesets; no package changes means success.
- Provide an empty changeset path for tests/CI-only PRs.
- Automate versioning/publishing with `changesets/action`; do not publish from a local authoring session.

## 8. Common Authoring Pitfalls

- Wrong package name or stale name after a rename → change never reaches the intended package.
- Unquoted scoped names or tabs in frontmatter → YAML parse failures.
- Bump chosen by effort instead of impact.
- Summary written for maintainers ("refactor internals") instead of consumers.
- Major bump with no migration instructions.
- Using an empty changeset to bypass a real release decision.
- Editing generated changelogs or versions by hand instead of letting `version` do it.
- Writing changesets in repos that use release-please/semantic-release; those tools read commits, not `.changeset`.

## Sources

- Changesets documentation: <https://github.com/changesets/changesets/tree/main/docs> (writing changesets, config, CLI, automating, FAQ, beyond npm)
- Semantic Versioning 2.0.0: <https://semver.org/>
