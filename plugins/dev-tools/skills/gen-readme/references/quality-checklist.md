# README Quality Checklist

Run **Gate 0** before drafting. Run the remaining gates after drafting and after every fix pass. The script catches mechanical issues; this list covers what a reader judges.

## Gate 0 — Scope and Approval

- [ ] Mode, scope (`root` / `packages` / `all`), and target files are listed explicitly.
- [ ] For a monorepo, workspace packages were inventoried and skipped package READMEs are named.
- [ ] Each target has a style and an explicit module ID list.
- [ ] The plan (scope + files + style + modules) was approved before drafting when replacing content or touching multiple files.
- [ ] Final files match the approved plan; any added/removed file or required section was re-confirmed.

**Blocking:** overwriting an existing README or adding package files without an approved plan.

## Gate 1 — Truth and Safety

- [ ] Every install, build, test, and run command traces to a manifest, Makefile, CI file, or verified `--help`.
- [ ] No invented benchmarks, user counts, version claims, or support promises.
- [ ] Every badge has a live source and a meaningful link.
- [ ] License matches the actual `LICENSE` file and owner.
- [ ] No secrets, tokens, private hostnames, personal emails, or internal URLs.
- [ ] Config examples show names and safe defaults only.
- [ ] External claims link to their evidence.

**Blocking:** any fabricated command or leaked secret.

## Gate 2 — First Screen

- [ ] Title matches the repository/package name.
- [ ] Pitch is one sentence and ≤120 characters.
- [ ] The next paragraph explains the problem and the differentiator, not the feature list.
- [ ] A proof point appears before deep explanation: screenshot, demo, or transcript.
- [ ] The fastest install/start command is visible in the first screen.
- [ ] Status callout (if any) is near the top and states the practical consequence.

**Blocking:** no clear pitch, or no usable start path for a functional project.

## Gate 3 — Onboarding Path

- [ ] Prerequisites are listed only when non-obvious.
- [ ] One default command; alternatives are clearly secondary.
- [ ] Commands are copy-paste ready and use correct fences.
- [ ] The minimal example produces the documented output.
- [ ] The reader knows the next step after the first command.
- [ ] Platform/package-manager variants are accurate.

**Blocking:** the documented quick start does not work or cannot be traced.

## Gate 4 — Scanability

- [ ] Heading hierarchy is valid (`#` → `##` → `###`; no skipped levels).
- [ ] A TOC exists when the README is ≥100 lines or has >5 level-two sections.
- [ ] TOC order matches the document and anchors resolve.
- [ ] Repeated sections use a consistent shape.
- [ ] Paragraphs are short; bullets carry one idea.
- [ ] Code fences have language hints where meaningful.
- [ ] Long detail is linked out, not pasted in.
- [ ] Rendered size stays under GitHub's 500 KiB truncation limit.

**Blocking:** broken anchors from a TOC that was not updated after renaming.

## Gate 4.5 — Optional Visuals and Credibility

- [ ] Banner, icons, screenshots, and charts exist, are compressed, and have alt text.
- [ ] Dark/light variants exist where needed, or the asset works on both backgrounds.
- [ ] Icons and brand logos are used within their license and do not imply endorsement.
- [ ] Charts and benchmarks link their source data, environment, and date.
- [ ] Dynamic badges, star history, and coverage stats link to their source and are not the sole proof.
- [ ] Demo videos have a poster/summary; live demos state access/reset behavior.
- [ ] Contributors, sponsors, roadmap, and maintainers are current and consented.
- [ ] Each optional element adds information; decoration-only blocks were removed.

**Blocking:** unlicensed or fabricated visuals, or a referenced local asset that does not exist.

## Gate 5 — Style Fit

- [ ] The chosen style's required sections are present.
- [ ] Style-specific content dominates; hybrid content stays subordinate.
- [ ] Internal-service READMEs include ownership, local dev, configuration, architecture, and operations.
- [ ] Monorepo root navigates; package detail lives in package READMEs.
- [ ] Every in-scope workspace package has a README, or an explicit skip reason.
- [ ] The root package table matches the workspace globs and its README links resolve.
- [ ] Published package READMEs sit at the package root and stand alone (name, install, public surface, usage, license).
- [ ] Vendored, fixture, and generated READMEs are excluded unless explicitly in scope.
- [ ] App READMEs include configuration and a runnable local/demo path.
- [ ] CLI READMEs include platform install and copy-paste command examples.
- [ ] Library READMEs include install, smallest correct usage, and API/doc links.

**Blocking:** a style contract section is missing without a stated reason.

## Gate 6 — Maintenance

- [ ] No `TODO`, `TBD`, `FIXME`, `<placeholder>`, or sample values remain.
- [ ] Relative links and images resolve.
- [ ] Renamed files/commands are reflected everywhere.
- [ ] Bilingual variants have aligned section order and a working switcher.
- [ ] The README does not duplicate a doc that will drift independently.
- [ ] Version-specific claims are dated or linked to a source.

**Blocking:** unresolved placeholders in a delivered README.

## Script Mapping

`scripts/readme_audit.py` checks the mechanical subset:

| Check | Gate |
|-------|------|
| Missing/empty README, missing H1 | 2 |
| Missing required sections for style | 5 |
| Broken local links/images | 1, 4.5, 6 |
| Broken TOC anchors | 4 |
| Heading level jumps | 4 |
| Unclosed code fences | 4 |
| Code fences without language hints | 4 |
| TOC missing at ≥100 lines | 4 |
| Long first paragraph / missing pitch | 2 |
| Empty image alt text | 4.5 |
| Local image over 1 MiB | 4.5 |
| Badges without links | 1 |
| Placeholders (`TODO`, `TBD`, `<...>`) | 6 |
| README > 500 KiB | 4 |
| No code block for command-oriented styles | 3 |
| License not last | 5 |

## Severity Policy

- **Error:** stop and fix before delivery. Broken files/links, missing title, unclosed fences, leaked placeholder scaffolding.
- **Warning:** fix, or record a one-line justification in the delivery report. Missing optional section, long paragraph, no TOC, unlinked badge.
- **Info:** context for the reviewer; no action required.

## Final Reader Test

Read the rendered README as three different people:

1. **Newcomer** — can I say what this is and run it without opening another file?
2. **Evaluator** — can I see evidence that it works and fits my constraints?
3. **Maintainer** — can I update this page without guessing which claims are stale?

If any answer is no, fix the page before delivery.
