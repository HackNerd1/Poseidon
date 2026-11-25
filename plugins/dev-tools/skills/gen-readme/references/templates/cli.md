<!--
TEMPLATE: cli
Use for command-line tools and developer executables.
Optional banner/icons/charts/community modules: see references/optional-elements.md (M21+).
Fill every <...>. Delete guidance comments and unused optional sections.
Add a TOC when the result reaches ~100 lines.
For a published package, place this file at the package root; npm renders it
on the package page and always includes it in the tarball.
-->
# <tool-name>

**<One sentence, ≤120 characters: what the tool does and why it is better/faster/simpler.>**

<p align="center">
  <img src="docs/assets/<demo>.gif" alt="<what the demo shows>" width="720">
</p>

- **<Outcome 1>** — <what the user can do now>.
- **<Outcome 2>** — <second differentiator>.
- **<Outcome 3>** — <third differentiator>.

## Installation

### <Platform / package manager — default>

```bash
<install-command>
```

### <Platform / package manager>

```bash
<install-command>
```

<details>
<summary>Build from source</summary>

```bash
<build-command>
```

</details>

## Shell integration

<Only include when the tool benefits from completion or shell hooks.>

```bash
# bash
<setup-command>
```

```zsh
# zsh
<setup-command>
```

## Usage

<One sentence introducing the smallest useful invocation.>

```bash
<minimal-command>
```

Expected output:

```text
<short realistic output>
```

<Next step or link to the command reference.>

## Common commands

| Command | What it does |
|---------|--------------|
| `<command>` | <one-line purpose> |
| `<command> --<flag>` | <one-line purpose> |

## Configuration

| Name | Default | Description |
|------|---------|-------------|
| `<ENV_VAR>` | `<safe default>` | <what it changes> |
| `--<flag>` | `<default>` | <what it changes> |

<Link to the full CLI reference.>

## Troubleshooting

### <Symptom>

**Cause:** <one line>.

**Fix:**

```bash
<diagnostic or fix command>
```

## Documentation

- [CLI reference](docs/cli.md) — <one-line scope>
- [Recipes](docs/recipes.md) — <one-line scope>
- [Architecture](docs/architecture.md) — <one-line scope>

<!-- Include only if CONTRIBUTING.md exists; otherwise link the team's real process or delete. -->
## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

<SPDX identifier> © <owner>. See [LICENSE](LICENSE).
<!--
If the package is private/unlicensed, replace with:
Internal and proprietary. Not for external distribution.
Do not link a LICENSE file that does not exist.
-->
