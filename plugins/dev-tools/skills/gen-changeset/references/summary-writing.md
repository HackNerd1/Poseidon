# Writing the Changeset Summary

The changeset body becomes the changelog entry users read when deciding whether to upgrade. Write it for that reader, not for the reviewer of the PR.

## 1. The Contract

A good summary answers three questions, in this order of importance:

1. **WHAT** changed — the public symbol, command, flag, config key, or behavior.
2. **WHY** it matters — the problem solved or the risk introduced, when not obvious.
3. **HOW** to update — required for breaking changes; useful for deprecations and new opt-ins.

Changesets' own guidance: WHAT the change is, WHY it was made if relevant to the consumer, HOW a consumer should update their code if they must. Not every entry needs all three at length.

## 2. Length by Bump

| Bump | Typical shape |
|------|----------------|
| `patch` | One sentence: fixed behavior + affected path. |
| `minor` | One to three sentences: new capability + how to use it; optional short snippet. |
| `major` | One paragraph naming the break + a migration block with before/after. |
| Empty | No body (delimiters only). |

Longer is not better. A concise entry that names the symbol and the effect beats a paragraph of context.

## 3. Writing Patterns

### Lead with the consumer-visible effect

- Good: `Added \`exportCsv()\` to export query results as CSV.`
- Good: `Fixed \`retry()\` dropping the final attempt when \`maxRetries\` was reached.`
- Weak: `Refactored the retry module and improved test coverage.`

### Name exact identifiers

Use the real spelling of exports, flags, config keys, environment variables, and error codes, in backticks. If the name changed, show both names.

```markdown
Renamed the `--output-format` flag to `--format`.
```

### State the condition, not just the outcome

For fixes, say what was wrong and for whom. For features, say when to use it.

```markdown
Fixed `parseDuration("1h30m")` returning `90` seconds instead of `5400`.
```

### Write migrations as instructions

Start with "To migrate", then a rename map or diff. Keep it executable by a reader who has the old code open.

````markdown
To migrate, replace the removed `legacyMode` option with `mode: "compat"`:

```diff
- createClient({ legacyMode: true })
+ createClient({ mode: "compat" })
```
````

### Match the repo's voice

Read several released changesets or `CHANGELOG.md` entries first. Match tense ("Added" vs "Adds" vs "Add"), capitalization, and language. If no precedent exists, use past tense for completed changes and sentence case for headings.

### Use structure only when it helps

A list is right for several independent renames or options. A code block is right for signatures and migrations. Leave one-line patches as prose.

## 4. Multi-Package Changesets

When one change spans packages:

- If every package gets the same bump and the same explanation is accurate, one changeset with multiple frontmatter entries is fine; the body should mention each affected surface.
- If the bumps differ, or one package has a breaking change and another only a patch, split into separate changesets — the changelog for each package must stand alone.
- Never write a package-specific summary on a package it does not describe ("SDK now supports X" in a CLI-only entry).

## 5. Language

- Follow the language of existing changesets and changelogs.
- No precedent → the language the user is writing in.
- Keep code identifiers, commands, and paths in their original form.
- Do not machine-translate established English terms such as "breaking change" or "deprecated" into invented equivalents; use the team's existing vocabulary.

## 6. Weak → Strong Examples

**Patch**

- Weak: `Fixed a bug in the parser.`
- Strong: `Fixed \`parseConfig()\` rejecting valid YAML anchors when \`strict\` was enabled.`

- Weak: `Updated dependencies.`
- Strong: `Updated \`undici\` to 7.x, fixing connection reuse after a 429 response.`

**Minor**

- Weak: `Added CSV support.`
- Strong: `Added \`exportCsv()\` and the \`acme export --format csv\` flag for exporting query results as CSV.`

- Weak: `Deprecated old API.`
- Strong: `Deprecated \`fetchAll()\`; use \`listAll()\` with \`paginate: false\`. \`fetchAll()\` will be removed in the next major release.`

**Major**

- Weak: `Breaking changes to the client API.`
- Strong:

````markdown
Replaced the positional `createClient(url, key)` signature with an options object and removed the `timeout` default.

To migrate:

```diff
- createClient("https://api.example.com", key)
+ createClient({ baseUrl: "https://api.example.com", apiKey: key })
```

Set `timeout` explicitly if you relied on the previous 30-second default.
````

## 7. Avoid

- Internal ticket IDs or commit hashes as the only content.
- "Misc fixes", "various improvements", "internal changes", "WIP", "see PR".
- Implementation narration that does not name a consumer-visible effect.
- Claims the diff does not support (new defaults, performance numbers, compatibility).
- Placeholders (`TODO`, `TBD`, `<package>`) left in the final artifact.
- Marketing language ("blazing fast", "revolutionary") in a changelog.
- Repeating the package name or bump in the body; the frontmatter already carries them.

## 8. Changelog Fallback (Keep a Changelog)

When no release tool owns the changelog, edit `CHANGELOG.md`:

- Keep an `Unreleased` section at the top; move entries into a version section at release time.
- Group under `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- Newest version first; ISO 8601 dates (`2026-11-25`); state that the project follows SemVer.
- Changelogs are for humans: curated, grouped, consistent — never a raw commit log.
- Link versions and sections when the file already does; do not invent link schemes.

## 9. Pre-Delivery Checklist

- [ ] The first sentence names the public symbol or behavior.
- [ ] The bump is provable from the text (new capability / correction / break).
- [ ] A `major` entry includes a migration path.
- [ ] Package names and identifiers are exact.
- [ ] No placeholders, ticket-only text, or unsupported claims.
- [ ] Voice and language match existing entries.
- [ ] The body makes sense without opening the PR.

## Sources

- Changesets writing guidance (WHAT/WHY/HOW): <https://github.com/changesets/changesets/blob/main/docs/guide/writing-changesets.md>
- Keep a Changelog 1.1.0: <https://keepachangelog.com/en/1.1.0/>
