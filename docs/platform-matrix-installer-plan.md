# Platform Matrix Installer Plan

## Goal

Make Poseidon reusable across Claude Code, Codex, and future agent platforms by keeping each skill in one canonical location and using a repository-level installer to handle platform-specific discovery paths, manifests, marketplaces, and adapters.

The guiding rule is:

- `plugins/*/skills/*` is the canonical skill source.
- Root `scripts/` contains repository-level install, generation, and validation tooling.
- Skill-local `plugins/*/skills/*/scripts/` remains runtime tooling for that specific skill.

## Target Structure

```text
scripts/
  platforms.yaml
  install.py
  validate.py
  adapters/
    __init__.py
    codex.py
    claude.py
    cursor.py
    windsurf.py

plugins/
  ruankao/
    skills/
    .claude-plugin/
    .codex-plugin/
  resume/
    skills/
    .claude-plugin/
    .codex-plugin/
  algo-coach/
    skills/
    .claude-plugin/
    .codex-plugin/
  dev-tools/
    skills/
    hooks/
    scripts/
    .claude-plugin/
    .codex-plugin/

.agents/
  plugins/
    marketplace.json
```

`cursor.py` and `windsurf.py` can start as placeholders. The first implementation should support Claude and Codex only.

## Platform Matrix

`scripts/platforms.yaml` should be the single source of truth for platform install paths and adapter behavior.

Initial shape:

```yaml
platforms:
  codex:
    implemented: true
    user_skill_path: "~/.agents/skills"
    project_skill_path: ".agents/skills"
    plugin_manifest: ".codex-plugin/plugin.json"
    marketplace_path: ".agents/plugins/marketplace.json"
    hook_template: "hooks/codex/hooks.json"
    hook_output: "hooks/hooks.json"
    supports_plugin: true
    install_mode: marketplace

  claude:
    implemented: true
    user_skill_path: "~/.claude/skills"
    project_skill_path: ".claude/skills"
    plugin_manifest: ".claude-plugin/plugin.json"
    marketplace_path: ".claude-plugin/marketplace.json"
    hook_template: "hooks/claude/hooks.json"
    hook_output: "hooks/hooks.json"
    supports_plugin: true
    install_mode: plugin

  cursor:
    implemented: false
    project_skill_path: ".cursor/skills"
    supports_plugin: false
    adapter: mdc
    install_mode: copy
```

## Installer Commands

The installer should support both interactive and non-interactive modes. With no arguments, it should open an interactive CLI. With explicit flags, it should run in scriptable mode for CI and automation.

Interactive mode:

```bash
python scripts/install.py
python scripts/install.py --interactive
```

Non-interactive mode:

```bash
python scripts/install.py --platform codex --scope repo
python scripts/install.py --platform codex --scope repo --dry-run
python scripts/install.py --platform claude --scope user --plugin ruankao
python scripts/install.py --all --scope user --dry-run
python scripts/install.py --platform codex --scope repo --plugin all --yes
python scripts/install.py --platform codex --scope repo --plugin all --generate-only
```

Use Python standard library only for the first implementation:

- `argparse` for non-interactive arguments.
- `input()` for interactive prompts.
- `json`, `pathlib`, and `shutil` for file operations.
- `--yes` to skip confirmation in automation.
- `--dry-run` to print the plan without writing files.
- `--generate-only` to write manifests and marketplace files without registering, installing, or enabling plugins in Codex.

Interactive flow:

```text
Poseidon Installer

? Select target platform
  > Codex
    Claude
    Cursor
    Windsurf
    All supported platforms

? Select install scope
  > Repo-local
    User-global

? Select plugin
  > All plugins
    ruankao
    resume
    algo-coach
    dev-tools

? Select operation mode
  > Dry run
    Apply changes

? Install and enable Codex plugins after generating files
  > Yes
    No, generate files only

Plan:
  - Generate plugins/ruankao/.codex-plugin/plugin.json
  - Generate plugins/resume/.codex-plugin/plugin.json
  - Update .agents/plugins/marketplace.json
  - Run codex plugin marketplace add <repo-root> --json
  - Run codex plugin add ruankao@poseidon --json
  - Validate 14 SKILL.md files

? Proceed? yes/no
```

Expected behavior:

- `--platform codex --scope repo`
  - Ensure each plugin has `.codex-plugin/plugin.json`.
  - Generate or update `.agents/plugins/marketplace.json`.
  - Point each marketplace entry to `./.codex/generated/plugins/<plugin-name>`.
  - Generate each Codex package from the canonical plugin source before install, excluding Claude-only defaults such as `hooks/hooks.json`.
  - Render `hooks/codex/hooks.json` to the generated package's `hooks/hooks.json` when a plugin provides Codex hooks.
  - Do not duplicate skill contents.
  - Unless `--generate-only` is present, register the repo marketplace with `codex plugin marketplace add <repo-root> --json`.
  - Unless `--generate-only` is present, install and enable selected plugins with `codex plugin add <plugin>@poseidon --json`.
- `--platform claude`
  - Validate existing `.claude-plugin/plugin.json` files.
  - Reuse `.claude-plugin/marketplace.json`.
  - Optionally copy or link skills for direct user-level skill install.
- `--plugin <name>`
  - Limit work to one plugin.
- `--dry-run`
  - Print intended file writes and install targets without modifying files.
- `--generate-only`
  - Skip Codex CLI marketplace registration and plugin install/enable commands.
- interactive mode
  - Build the same operation plan as non-interactive mode.
  - Show every file write before execution.
  - Require confirmation unless `--yes` is present.

## Validation Commands

```bash
python scripts/validate.py --platform codex
python scripts/validate.py --platform claude
python scripts/validate.py --all
```

Validation should check:

- Every `SKILL.md` has valid frontmatter.
- Skill names use lowercase hyphen-case.
- Skill descriptions are present and not overly long.
- Codex plugin manifests use `"skills": "./skills/"`.
- Claude plugin manifests still parse.
- Marketplace entries point to generated Codex package folders.
- Generated files are in sync with canonical plugin metadata.
- Generated Codex packages do not include default hooks unless those hooks are Codex-compatible.

## Skill Frontmatter Policy

Canonical `SKILL.md` files should avoid platform-specific frontmatter.

Preferred:

```yaml
---
name: write-paper
description: 软考论文从零写作。当用户提供论文题目（题干）要求写一篇新论文时触发。
---
```

Move parameter hints such as `arguments` into the body:

```markdown
## 输入

- 论文题目或题干
- 可选：指定方法论、项目背景、输出路径
```

## Hooks Policy

Hooks should not be treated as generic plugin metadata. They are platform-specific integration code.

Recommended layout:

```text
plugins/dev-tools/hooks/
  hooks.json        # legacy Claude-compatible default
  claude/hooks.json
  codex/hooks.json
```

Shared executable logic should stay in `plugins/dev-tools/scripts/`, while event names, environment variables, and matcher syntax live in platform-specific hook configs.

Codex hook templates may use installer-rendered placeholders:

- `{{PLUGIN_NAME}}`
- `{{PLUGIN_VERSION}}`
- `{{MARKETPLACE_NAME}}`
- `{{CODEX_CACHE_PLUGIN_ROOT}}`
- `{{CODEX_CACHE_PLUGIN_ROOT_WINDOWS}}`

Codex hook configs must not use `async: true` or Claude-only variables such as `${CLAUDE_PLUGIN_ROOT}`.
Notification-style Codex hooks must use `--quiet --best-effort` so they do not write non-JSON text to stdout or fail the agent turn when the local desktop notification backend is unavailable. Click-to-focus is platform-specific: Windows uses a detached NotifyIcon listener, macOS requires `terminal-notifier` for reliable click activation, and Linux requires an action-capable notification daemon plus `xdotool` or `wmctrl`.

## Implementation Phases

### Phase 1: Codex Packaging

- Add `.codex-plugin/plugin.json` for each plugin.
- Add `.agents/plugins/marketplace.json`.
- Generate Codex package folders under `.codex/generated/plugins/`.
- Add initial `scripts/platforms.yaml`.
- Add `scripts/validate.py` with basic skill and manifest checks.

### Phase 2: Installer

- Add `scripts/install.py`.
- Implement default interactive mode.
- Implement `--platform codex`, `--scope repo`, `--plugin`, `--dry-run`, `--yes`, and `--generate-only`.
- Ensure non-dry-run Codex installs register the marketplace and enable the selected plugins.
- Add `scripts/adapters/codex.py`.
- Keep Claude adapter validation-only at first.

### Phase 3: Skill Cleanup

- Move `arguments` out of all `SKILL.md` frontmatter.
- Normalize script path instructions to use the current skill directory.
- Ensure references are described as skill-local resources.

### Phase 4: Claude Parity

- Add `scripts/adapters/claude.py`.
- Validate existing `.claude-plugin` manifests.
- Preserve current Claude marketplace behavior.

### Phase 5: Optional Rule Adapters

- Add Cursor adapter to generate `.mdc` files.
- Add Windsurf adapter only if the skill body can fit its rule size limits.
- Keep generated adapter files out of canonical skill sources unless they are intentionally committed.

## Acceptance Criteria

- `python scripts/validate.py --all` passes.
- Codex can discover all four plugins from `.agents/plugins/marketplace.json`.
- Claude install docs and existing plugin metadata still work.
- No skill content is duplicated for Codex.
- Hook migration is explicit and does not silently reuse Claude-only hook configuration.

## Open Decisions

- Whether generated `.codex-plugin/plugin.json` files should be committed or produced on install.
- Whether user-level installs should copy files or create symlinks.
- Whether Cursor/Windsurf adapters are in scope for the first release.
