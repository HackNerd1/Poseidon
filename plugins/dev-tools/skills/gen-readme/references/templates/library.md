<!--
TEMPLATE: library
Use for packages/SDKs that developers install and import.
Optional banner/icons/charts/community modules: see references/optional-elements.md (M21+).
Fill every <...>. Delete guidance comments, unused optional sections, and
alternatives that do not apply. Add a TOC when the result reaches ~100 lines.
For a published package, place this file at the package root; npm renders it
on the package page and always includes it in the tarball.
-->
# <project-name>

[![CI](https://github.com/<org>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<org>/<repo>/actions/workflows/ci.yml)
[![<registry>](https://img.shields.io/<registry>/v/<package>.svg)](<registry-url>)
[![License](https://img.shields.io/badge/license-<SPDX>-blue.svg)](LICENSE)

**<One sentence, ≤120 characters: what it is, who it is for, and why it is different.>**

<2–3 sentences: the problem, the approach, and the outcome. Link one unfamiliar concept if useful.>

- **<Outcome 1>** — <what the user can do now>.
- **<Outcome 2>** — <second differentiator>.
- **<Outcome 3>** — <third differentiator>.

## Installation

### Requirements

- <Runtime> <version>+
- <Optional system dependency>

```bash
<install-command>
```

<One sentence confirming what was installed and what to do next.>

<details>
<summary>Other installation options</summary>

```bash
# <package manager or platform>
<alternative-command>
```

</details>

## Quick start

```<language>
<smallest complete, runnable example>
```

Expected output:

```text
<short realistic output>
```

<Link to a longer example or guide.>

## Usage

### <Capability>

<One sentence describing the capability.>

```<language>
<runnable example>
```

<Link to the full guide for this capability.>

### <Capability>

<One sentence describing the capability.>

```<language>
<runnable example>
```

## API

<Link to the API reference. If the surface is small, list the primary exports with one-line descriptions.>

## Compatibility

| Runtime | Supported |
|---------|-----------|
| <runtime> | <version range> |
| <OS/platform> | <supported list> |

## Documentation

- [Getting started](docs/getting-started.md) — <one-line scope>
- [API reference](docs/api.md) — <one-line scope>
- [Examples](examples/) — <one-line scope>

<!-- Include only if CONTRIBUTING.md exists; otherwise link the team's real process or delete. -->
## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup, test, and review requirements.

```bash
<test-command>
```

## License

<SPDX identifier> © <owner>. See [LICENSE](LICENSE).
<!--
If the package is private/unlicensed, replace with:
Internal and proprietary. Not for external distribution.
Do not link a LICENSE file that does not exist.
-->
