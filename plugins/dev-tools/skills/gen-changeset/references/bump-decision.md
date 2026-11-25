# Choosing the Version Bump

SemVer is the contract: MAJOR for incompatible public API changes, MINOR for backward-compatible functionality, PATCH for backward-compatible fixes. Changesets maps these directly to `major`, `minor`, `patch`.

## 1. The Decision Ladder

Ask in order; stop at the first yes.

| Question | Bump |
|----------|------|
| Would correct existing consumer code, config, or a supported runtime stop working? | `major` |
| Is new public capability available without breaking existing usage? | `minor` |
| Does behavior change in a way that fixes incorrect or unintended behavior while remaining compatible? | `patch` |
| Is nothing consumer-visible changed? | no release |

"Public" means anything a consumer can depend on: exported functions/types, CLI commands and flags, config schema and defaults, HTTP/API contracts of a published service, error types, emitted output, supported versions, and package `exports`/`bin`.

## 2. Surface-by-Surface Examples

| Change | Bump | Why |
|--------|------|-----|
| Remove/rename an exported symbol or CLI flag | `major` | Consumer references break |
| Add a required parameter to an existing function | `major` | Existing calls become invalid |
| Change a return type or response shape | `major` | Consumer destructuring/type checks break |
| Raise the minimum Node/runtime version | `major` | Supported environments break |
| Change a default value that alters behavior | `major` | Silent behavior change; consumers must opt in explicitly |
| Change a peer dependency range incompatibly | `major` | Install/resolution breaks |
| Add a new exported function, optional option, or subcommand | `minor` | Opt-in capability |
| Deprecate a public API without removing it | `minor` | SemVer treats deprecation as new public functionality |
| Add an optional field to a response | `minor` | Compatible addition |
| Fix a bug while keeping the same API | `patch` | Intended behavior restored |
| Performance/accessibility/security fix, no API change | `patch` | Compatible correction |
| Internal refactor, tests, CI, scripts, formatting | none | Nothing consumer-visible |
| Update a dev dependency or lockfile only | none | Not shipped |
| Update a runtime dependency within a compatible range | `patch` (usually) | Shipped code changes; confirm no API impact |

When a single change spans surfaces, the highest required bump wins.

## 3. Breaking Changes in Detail

A breaking change needs all three:

1. The correct bump (`major`).
2. A summary that names the break.
3. A migration path: rename map, before/after snippet, or config transformation.

Useful migration forms:

```markdown
To migrate, replace `fetchUsers()` with `listUsers()` and read `result.items` instead of the returned array.
```

```markdown
The `legacy` option was removed. Delete it from your config; equivalent behavior is now the default.
```

```markdown
Node 18 is no longer supported. Upgrade to Node 20 or later before updating.
```

Do not mark a cosmetic fix as `major` to "be safe": majors impose upgrade work and review burden. Do not hide a real break in `patch`: consumers upgrade automatically and break silently.

## 4. `0.x` Projects

SemVer says anything may change in `0.y.z`, and `1.0.0` defines the public API. Changesets still uses the three bump types:

- Breaking change in `0.x` → `major` (for example `0.4.0 → 1.0.0` under strict SemVer; many teams instead treat the first stable release as the graduation point and accept `0.5.0`).
- New capability → `minor` (`0.4.0 → 0.5.0`).
- Bug fix → `patch` (`0.4.0 → 0.4.1`).

When the repo documents a pre-1.0 policy (for example, breaking changes as `minor`), follow the documented policy and state it in the report. Graduating to `1.0.0` is a product decision — ask, do not slip it into a feature changeset.

## 5. Private, Ignored, and Internal Packages

- A private app that is not versioned or published (`privatePackages.version: false`, the default) gets no changeset.
- A private package inside a fixed group that *is* versioned still needs a bump when its public surface changes.
- A package in `ignore` is excluded from releases. Naming it together with released packages can make `changeset version` fail; exclude it and tell the user.
- For a monorepo of internal libraries that are published to a private registry, treat consumers exactly like external ones.

## 6. Dependency-Only Changes

| Situation | Bump |
|-----------|------|
| `package.json` dependency range widened/narrowed compatibly | `patch` for the package, if shipped |
| Dependency requires a new peer range | `major` when consumers must change; otherwise `minor` |
| Lockfile-only churn, no manifest change | none |
| Dev dependency/tooling upgrade | none |
| Internal workspace dependency changed but dependent's surface did not | dependent usually none; the changed package gets its own bump |

Changesets handles internal dependency range updates during `version`; do not add dependent packages just to force a range refresh.

## 7. Fixed and Linked Groups

- **Fixed** (`fixed`): every package in the group releases the same version. Apply the highest bump needed by any member and list all members that must move together.
- **Linked** (`linked`): packages share the highest version as a floor and bump together to the next shared version. The highest bump in the group governs.

Read the config before writing; both accept picomatch patterns.

## 8. Tie-Breakers and Failure Modes

- When `minor` vs `patch` is genuinely unclear: does an existing consumer have to read release notes to stay correct? If yes, `minor`; if no, `patch`.
- When `major` vs `minor` is unclear: search for existing consumers inside the repo and check tests/types; if any call site must change, it is `major`.
- Never bump based on lines changed, review effort, or "importance".
- Never ship a changeset for release tooling with the wrong bump because the user said "just patch it" — record the deviation and the risk in the report.
- After choosing, verify the summary proves the bump: a `minor` summary must describe new capability; a `major` summary must describe the break and migration.

## Sources

- Semantic Versioning 2.0.0: <https://semver.org/>
- Changesets config and versioning docs: <https://github.com/changesets/changesets/tree/main/docs/guide>
- Changesets increment implementation (`semver.inc` semantics): `packages/assemble-release-plan/src/increment.ts`
