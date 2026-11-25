# README Style Catalog

Five primary styles, the repo signals that select them, and the section contract each one must satisfy. Choose one primary style per README; hybrid content stays subordinate.

## Style Matrix

| Style | Primary reader | Job of the README | Template |
|-------|----------------|-------------------|----------|
| **library** | Developers who will import/install a package | Prove the API is useful, get it installed, show the smallest correct usage | `templates/library.md` |
| **cli** | Developers who will run a command | Show the tool in action, install it on the reader's platform, teach the core commands | `templates/cli.md` |
| **app** | End users, operators, and contributors of a deployed product | Show the product, get it running locally or via a hosted demo, explain configuration | `templates/app.md` |
| **monorepo** | Contributors navigating many packages | Explain what lives where, give one shared quick start, route to package READMEs | `templates/monorepo.md` |
| **internal-service** | Teammates and on-call engineers | Explain purpose, ownership, local development, configuration, and operations | `templates/internal-service.md` |

Fallback: `generic` (title, description, install, usage, license) when the repo has no clear signal. Use it only as a starting point, not as a final style choice for complex projects.

## Multi-README Scope

In a monorepo, style is chosen **per file**:

| Target | Style | Why |
|--------|-------|-----|
| Root `README.md` | `monorepo` | It navigates packages and repo-wide setup |
| Published package | `library` or `cli` | Its reader installs/imports/runs that package |
| Deployed app | `app` | Its reader runs or uses the product |
| Team service | `internal-service` | Its reader operates the service |

Rules:

- The root README links to every in-scope package README; it does not absorb package install/API detail.
- A package README must stand alone: package name, install command, public surface (`exports` / `bin` / `main`), usage, and license/compatibility.
- npm renders a package-root `README.md` on the package page and always includes it in the published package. Treat it as a public deliverable for published packages.
- Do not use `monorepo` style for a package README or `library` style for the workspace root.
- Scope must be explicit: `root`, `packages`, or `all`. List skipped package READMEs in the plan.

## Optional Enhancements

Visual, credibility, community, and navigation extras live in `references/optional-elements.md` (`M21`–`M36`): banner/logo, tech-stack icons, demo video, charts/benchmarks, star history, security policy, citation, contributors, sponsors, roadmap, changelog, support, TOC, background, maintainers, and code of conduct.

Rules:

- Optional modules never satisfy a required section of a style.
- They are never enabled by default; offer them only when the user asks or a public README would clearly benefit.
- Add them to the plan table with their M-ID and get approval like any other scope change.
- Prefer a small set that adds information over a wall of decoration.

## Selection Signals

Score each signal you can verify. Strong signals count 3, medium 2, weak 1.

### library

| Signal | Strength |
|--------|----------|
| Manifest declares `main` / `exports` / package metadata for npm, PyPI, crates.io, Maven, NuGet | Strong |
| Public API docs or exported symbols are the main surface | Strong |
| No executable entry point (`bin`) | Medium |
| Examples import the package (`import x from ...`, `from x import ...`) | Medium |
| Versioned releases / changelog aimed at consumers | Weak |

### cli

| Signal | Strength |
|--------|----------|
| Manifest `bin` field or an installed executable name | Strong |
| `cmd/`, `src/main.rs`, `main.go`, argparse/clap/cobra/commander entry point | Strong |
| README examples are shell commands with flags or pipes | Medium |
| Shell completion, `--help`, or man-page generation | Medium |
| Install instructions target Homebrew, apt, scoop, cargo install, etc. | Weak |

### app

| Signal | Strength |
|--------|----------|
| Web/mobile/desktop app framework with routes, pages, or UI entry points | Strong |
| `docker-compose.yml`, deployment manifests, or hosting config | Strong |
| `.env.example` with runtime configuration | Medium |
| Screenshots or demo URL in repo docs | Medium |
| No package-publishing metadata | Medium |

### monorepo

| Signal | Strength |
|--------|----------|
| Workspace config (`pnpm-workspace.yaml`, npm/yarn workspaces, `turbo.json`, `nx.json`, `Cargo.toml` workspace, `go.work`) | Strong |
| Multiple packages/apps with their own manifests | Strong |
| Root scripts that fan out to packages | Medium |
| Changesets / release tooling spanning packages | Weak |

### internal-service

| Signal | Strength |
|--------|----------|
| Private repository or internal-only distribution | Strong |
| Deployment manifests (Kubernetes, Helm, Terraform, internal CI deploy) | Strong |
| Ops docs: runbooks, dashboards, alerts, SLOs, on-call | Strong |
| Service catalog metadata or ownership files (`CODEOWNERS`, `OWNERS`) | Medium |
| No public install channel | Medium |

## Selection Procedure

1. Record signals with evidence in the plan:
   ```md
   **Style signals:** cli (bin field in package.json; src/cli.ts; shell examples in docs/)
   ```
2. Score. If the top style has a clear margin (roughly 2× the runner-up) and matches user intent, recommend it and proceed.
3. If the top two are close, present the finalists and ask. Keep the choice to at most four options.
4. If no style scores above the fallback threshold, use `generic` and say which facts are missing.
5. Record the decision and the reason in the plan; do not silently switch styles later.

### Question Template

> This repo fits **<style A>** and **<style B>**. Which README should I write?
> - **<Style A>** — <what the reader gets; typical sections>
> - **<Style B>** — <what the reader gets; typical sections>

## Section Contracts

The audit script checks these headings per file. Matching is case-insensitive and accepts the aliases listed. A style's required sections are the contract; modules in `references/modules.md` are implementations of those sections.

### library

Required:

- Title (H1)
- Short description / pitch (first paragraph)
- Installation — `install`, `installation`, `getting started`, `quick start`, `setup`, `安装`, `快速开始`
- Usage — `usage`, `how to use`, `examples`, `使用`, `用法`, `示例`
- License — `license`, `licence`, `许可证`, `许可`

Recommended:

- API / reference
- Compatibility / requirements
- Contributing
- Documentation links
- Changelog link

### cli

Required:

- Title
- Installation
- Usage / examples
- License

Recommended:

- Highlights / features
- Shell integration / completion
- Configuration / options table
- Troubleshooting
- Platform support
- Links to full CLI reference

### app

Required:

- Title
- Quick start / installation / getting started
- Configuration / environment variables
- Usage / features / how it works

Recommended:

- Screenshot or demo link
- Project structure
- Deployment
- Roadmap / status
- Contributing
- License (or explicit proprietary/internal notice)

### monorepo

Required:

- Title
- Packages / repository structure
- Quick start / installation
- Contributing / development
- License

Recommended:

- Package table with links to each package README
- Shared tooling and commands
- Architecture map
- Release / changeset workflow

### internal-service

Required:

- Title / service overview
- Local development / getting started
- Configuration
- Architecture / design
- Operations / runbook / deployment / monitoring
- Ownership / maintainers / contact / support

Recommended:

- Status, tier, SLO
- Dashboards, alerts, logs
- Data sensitivity / security notes
- ADR links
- API docs link

### generic

Required:

- Title
- Installation / quick start
- Usage
- License

## Hybrid Rules

| Combination | Primary style | Treatment |
|-------------|---------------|-----------|
| Library + first-class CLI | `library` when most users import; `cli` when most users run the binary | Secondary section after usage; link its full reference |
| App + public SDK | `app` | SDK gets its own section and link; do not let it dominate the first screen |
| Monorepo of services | `monorepo` | Root navigates; each service README may use `internal-service` |
| Internal service + CLI | `internal-service` | CLI reference is a section; operations still come before deep CLI options |
| Framework/plugin with examples | `library` | Examples are usage proof; link the example directory |

## Length Choice

| Choice | Target | Use when |
|--------|--------|----------|
| **One-screen** | ≤120 lines | Small library, early project, internal tool with a short lifecycle |
| **Full guide** | 150–400 lines | CLI with many commands, app with configuration/deployment, monorepo, service with operations |

Beyond roughly 400 lines, move detail into `docs/` and keep the README as the map. GitHub truncates rendered content beyond 500 KiB.
