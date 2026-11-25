# Release Tooling Modes

One repository, one release system. Detect it before writing; never add a second one. If detection is ambiguous, ask instead of guessing.

## 1. Detection

| Signal | Mode | What consumes the change |
|--------|------|--------------------------|
| `.changeset/config.json` | Changesets | `.changeset/*.md` files |
| `release-please-config.json`, `.release-please-manifest.json` | release-please | Conventional commit messages on the target branch |
| `.releaserc`, `.releaserc.json`, `.releaserc.js`, `release.config.js` | semantic-release | Conventional commit messages in CI |
| `lerna.json` | Lerna | Commit messages (conventional mode) or manual version command |
| `cliff.toml` | git-cliff | Commit messages, rendered by the cliff config |
| `CHANGELOG.md` with no tool config | Keep a Changelog (manual) | Hand-edited `CHANGELOG.md` |
| None of the above | Undecided | Ask: adopt Changesets, or write a changelog entry |

Check `package.json` scripts and CI workflows for the actual command (`release`, `version`, `publish`) before assuming. A `CHANGELOG.md` can coexist with an automated tool; the tool still owns the content.

## 2. Changesets

Deliverable: a new `.changeset/<name>.md` file.

- Follow `changesets-format.md` for format and config.
- Validate with `scripts/changeset_lint.py` and `changeset status --since <base>`.
- Do not run `changeset version` or `changeset publish`; a release workflow or maintainer does that.
- Do not hand-edit generated `CHANGELOG.md` or `package.json` versions; they are outputs of `version`.

## 3. release-please

release-please reads Conventional Commits merged to the release branch, opens/updates a release PR, and updates changelogs and version files itself.

Deliverable: a Conventional Commit message (and a PR title that follows the same format), not a changeset file.

```text
feat(sdk): add CSV export via exportCsv()

Adds exportCsv() for exporting query results. The CLI exposes it as
acme export --format csv.
```

Breaking change:

```text
feat(sdk)!: replace positional client arguments with an options object

BREAKING CHANGE: createClient(url, key) is replaced by
createClient({ baseUrl, apiKey }). The previous 30-second default timeout
was removed; set timeout explicitly if you relied on it.
```

Rules:

- Use the commit types the repo's config recognizes (`feat`, `fix`, `perf`, `deps`, `revert`; docs/chore/test/ci usually no release).
- A breaking change needs `!` before the colon and/or a `BREAKING CHANGE:` footer; the footer text is the migration note.
- The PR body can carry the longer explanation; keep the commit subject consumer-readable.
- Do not edit the release PR's generated files; release-please regenerates them.

## 4. semantic-release

semantic-release derives the next version and changelog from commit messages during CI. Manual version or changelog edits are overwritten or cause conflicts.

Deliverable: a Conventional Commit message that satisfies the repo's `@semantic-release/commit-analyzer` preset (Angular by default).

- `fix:` → patch, `feat:` → minor, `BREAKING CHANGE:` footer or `!` → major.
- Inspect `.releaserc*` for `branches`, `preset`, `tagFormat`, and plugin overrides before writing.
- Never create `.changeset` files or edit `CHANGELOG.md` here.
- If the user asks for a changelog entry, output the text for review, not a file the tool will manage.

## 5. Lerna

Lerna repositories version with `lerna version` (fixed or independent mode) and may generate changelogs from conventional commits.

- Check `lerna.json` for `version` (fixed number) vs `"independent"`, and for `command.version.conventionalCommits`.
- Deliverable: a Conventional Commit message, or a proposed changelog entry when the repo versions manually.
- Do not run `lerna version` or `lerna publish`; do not invent a `.changeset` folder.

## 6. git-cliff

`cliff.toml` defines commit parsing and changelog rendering. git-cliff is commit-driven.

- Deliverable: a Conventional Commit message that matches the configured `commit_parsers` and groups.
- Read the config's group names and skip rules; a type the config skips will not appear in the changelog.
- Do not edit the generated changelog.

## 7. Keep a Changelog (Manual)

Only when no tool owns releases:

1. Edit `CHANGELOG.md`, not a new file.
2. Put the entry under `## [Unreleased]`, creating the section if needed.
3. Group under `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
4. Keep newest-first ordering, ISO 8601 dates (`2026-11-25`), and the project's link style.
5. Do not invent a version number or date for an unreleased change; the maintainer moves entries at release time.
6. Show the proposed diff to the user before writing when the file has an established structure.

## 8. Conventional Commit Quick Reference

```text
<type>(<scope>)!: <description>

[optional body]

[optional footer(s)]
```

| Type | Release effect (default) |
|------|--------------------------|
| `feat` | minor |
| `fix` | patch |
| `perf` | patch (preset-dependent) |
| `deps` | patch (preset-dependent) |
| `refactor`, `docs`, `test`, `ci`, `chore`, `build`, `style` | none by default |
| any type with `!` or `BREAKING CHANGE:` | major |

The body states WHAT and WHY; the `BREAKING CHANGE:` footer states HOW to migrate. Keep the description under ~72 characters and in the imperative mood.

## 9. Mixed or Unknown Setups

- Two tools configured → stop and report the conflict; ask which owns releases.
- A custom script publishes versions → read it before writing anything; it may consume a file convention not covered here.
- Monorepo with per-package release configs → follow the config for the package being changed, not the root guess.
- No tool and no changelog → ask whether to adopt Changesets (requires `package.json` per versioned package) or start a `CHANGELOG.md`. Do not scaffold silently.

## Sources

- Conventional Commits 1.0.0: <https://www.conventionalcommits.org/en/v1.0.0/>
- Changesets automating guide: <https://github.com/changesets/changesets/blob/main/docs/guide/automating.md>
- Keep a Changelog 1.1.0: <https://keepachangelog.com/en/1.1.0/>
