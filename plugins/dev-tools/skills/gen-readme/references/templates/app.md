<!--
TEMPLATE: app
Use for web, mobile, desktop, or self-hosted applications.
Optional banner/icons/charts/community modules: see references/optional-elements.md (M21+).
Fill every <...>. Delete guidance comments and unused optional sections.
Add a TOC when the result reaches ~100 lines.
-->
# <product-name>

**<One sentence, ≤120 characters: what the product does, who it is for, and the key benefit.>**

<p align="center">
  <img src="docs/assets/<screenshot>.png" alt="<what the screenshot shows>" width="720">
</p>

**Live demo:** https://<demo-url> · **Docs:** https://<docs-url>

## Features

- **<Outcome 1>** — <what the user can do>.
- **<Outcome 2>** — <second differentiator>.
- **<Outcome 3>** — <third differentiator>.

## Quick start

### Requirements

- <Runtime> <version>+
- <Database/service dependency>

```bash
<clone-or-install-command>
<env-setup-command>
<run-command>
```

Open <http://localhost:<port>>.

<details>
<summary>Run with Docker</summary>

```bash
<docker-compose-command>
```

</details>

## Configuration

Copy `.env.example` to `.env` and set the values for your environment.

| Name | Default | Required | Description |
|------|---------|----------|-------------|
| `<ENV_VAR>` | `<safe default>` | <yes/no> | <what it changes> |

Never commit secrets. <Link to the full configuration guide.>

## Usage

### <Primary workflow>

<One or two sentences describing the workflow, then a screenshot or short steps list.>

1. <Step one.>
2. <Step two.>
3. <Step three.>

## Project structure

```text
<path>/          <one-line purpose>
<path>/          <one-line purpose>
<path>/          <one-line purpose>
```

## Deployment

<One paragraph: supported deployment targets and the pipeline that ships them. Link the deploy guide.>

## Roadmap

- [x] <Shipped capability>
- [ ] <Next capability>
- [ ] <Later capability>

<!-- Include only if CONTRIBUTING.md exists; otherwise link the team's real process or delete. -->
## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, test commands, and review expectations.

```bash
<test-command>
```

## License

<SPDX identifier> © <owner>. See [LICENSE](LICENSE).
<!--
Proprietary/internal app variant:
Internal and proprietary. Not for external distribution.
Do not link a LICENSE file that does not exist.
-->
