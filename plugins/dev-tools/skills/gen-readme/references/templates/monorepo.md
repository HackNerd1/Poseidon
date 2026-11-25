<!--
TEMPLATE: monorepo
Use for repositories with multiple packages/apps managed together.
Optional banner/icons/charts/community modules: see references/optional-elements.md (M21+).
Fill every <...>. Delete guidance comments and unused optional sections.
The root README navigates; package detail belongs in each package README.
Give each package README its own library/cli/app/internal-service template.
-->
# <repo-name>

**<One sentence, ≤120 characters: what the repo delivers as a whole.>**

<2–3 sentences: why the packages live together and what the shared tooling provides.>

## Packages

<!-- Canonical navigation. Every in-scope package must appear here with a working README link. -->

| Package | Path | Purpose | README |
|---------|------|---------|--------|
| `<package-a>` | `packages/<a>` | <one-line purpose> | [README](packages/<a>/README.md) |
| `<package-b>` | `packages/<b>` | <one-line purpose> | [README](packages/<b>/README.md) |
| `<app-a>` | `apps/<a>` | <one-line purpose> | [README](apps/<a>/README.md) |

## Quick start

### Requirements

- <Runtime> <version>+
- <Package manager> <version>+

```bash
<install-command>
<build-command>
<test-command>
```

## Common commands

| Command | What it does |
|---------|--------------|
| `<command>` | <one-line purpose> |
| `<command>` | <one-line purpose> |
| `<command> --filter <package>` | <one-line purpose> |

<!-- Optional: include this tree only if it adds information beyond the package table
     (for example tooling/ or docs/). Otherwise delete the section to avoid duplication. -->
## Repository structure

```text
apps/            <one-line purpose>
packages/        <one-line purpose>
tooling/         <one-line purpose>
docs/            <one-line purpose>
```

## Architecture

<One short paragraph or Mermaid diagram showing how packages/apps depend on each other. Link the architecture doc.>

## Release workflow

<One paragraph: versioning, changesets/release command, and where release notes live.>

<!-- Include only if CONTRIBUTING.md exists. Otherwise link the team's real process or delete. -->
## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Before opening a pull request:

```bash
<lint-command>
<test-command>
```

## License

<SPDX identifier> © <owner>. See [LICENSE](LICENSE).
<!--
Internal / unlicensed variant:
Internal and proprietary. Not for external distribution.
-->
