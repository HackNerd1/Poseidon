# Platform Matrix Installer Plan

## Goal

Make Poseidon reusable across Claude Code, Codex, and future agent platforms by keeping each skill in one canonical location and using a repository-level installer to handle platform-specific discovery paths, manifests, marketplaces, and adapters.

The guiding rule is:

- `plugins/*/skills/*` is the canonical skill source.
- `plugins/plugin-metadata.json` is the canonical plugin and marketplace metadata source.
- Root `scripts/` contains repository-level install, generation, and validation tooling.
- Skill-local `plugins/*/skills/*/scripts/` remains runtime tooling for that specific skill.

## Target Structure

```text
scripts/
  platforms.yaml
  install.py
  validate.py
  hook_intents.py
  adapters/
    __init__.py
    codex.py
    claude.py
    cursor.py
    windsurf.py

plugins/
  plugin-metadata.json
  ruankao/
    skills/
  resume/
    skills/
  algo-coach/
    skills/
  dev-tools/
    skills/
    hooks/
    scripts/

.agents/
  plugins/
    marketplace.json        # installer-generated, ignored

.codex/
  generated/
    plugins/
      <plugin>/
        .codex-plugin/plugin.json

.claude/
  generated/
    plugins/
      <plugin>/
        .claude-plugin/plugin.json

.claude-plugin/
  marketplace.json          # installer-generated, ignored
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
python scripts/install.py --platform claude --scope repo --plugin ruankao
python scripts/install.py --all --scope repo --dry-run
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
  - Read plugins/plugin-metadata.json
  - Generate .codex/generated/plugins/ruankao/.codex-plugin/plugin.json
  - Generate .codex/generated/plugins/resume/.codex-plugin/plugin.json
  - Generate .agents/plugins/marketplace.json
  - Run codex plugin marketplace add <repo-root> --json
  - Run codex plugin add ruankao@poseidon --json
  - Validate 14 SKILL.md files

? Proceed? yes/no
```

Expected behavior:

- `--platform codex --scope repo`
  - Read canonical Codex plugin metadata from `plugins/plugin-metadata.json`.
  - Generate each plugin's `.codex-plugin/plugin.json` inside `.codex/generated/plugins/<plugin>/`.
  - Generate or update `.agents/plugins/marketplace.json` from `plugins/plugin-metadata.json`.
  - Point each marketplace entry to `./.codex/generated/plugins/<plugin-name>`.
  - Generate each Codex package from the canonical plugin source before install, excluding Claude-only defaults such as `hooks/hooks.json`.
  - Render `hooks/codex/hooks.json` to the generated package's `hooks/hooks.json` when a plugin provides Codex hooks.
  - Do not duplicate skill contents.
  - Unless `--generate-only` is present, register the repo marketplace with `codex plugin marketplace add <repo-root> --json`.
  - Unless `--generate-only` is present, install and enable selected plugins with `codex plugin add <plugin>@poseidon --json`.
- `--platform claude`
  - Read canonical plugin metadata from `plugins/plugin-metadata.json`.
  - Generate each plugin's `.claude-plugin/plugin.json` inside `.claude/generated/plugins/<plugin>/`.
  - Generate or update `.claude-plugin/marketplace.json` from `plugins/plugin-metadata.json`.
  - Point each marketplace entry to `./.claude/generated/plugins/<plugin-name>`.
  - Optionally copy or link skills for direct user-level skill install in a later phase.
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
- Claude generated plugin manifests still parse and match canonical metadata.
- Marketplace entries point to generated Codex package folders.
- Generated files are in sync with canonical plugin metadata.
- Generated marketplace files are in sync with canonical marketplace metadata.
- Source plugin directories do not maintain hand-written `.codex-plugin/plugin.json` files.
- Source plugin directories do not maintain hand-written `.claude-plugin/plugin.json` files.
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

The long-term source of truth should be hook intent files, not hand-written
platform hook JSON. Intent files describe the semantic event and shared command
behavior once; the installer renders Claude/Codex hook JSON from that source
using each platform's event names, root variables, async support, stdout rules,
and Windows command variants.

Recommended layout after the intent migration:

```text
plugins/dev-tools/hooks/
  intents/
    notify-response-ready.yaml
    notify-permission-required.yaml
```

Shared executable logic should stay in `plugins/dev-tools/scripts/`, while event
names, environment variables, matcher syntax, async behavior, and stdout policy
live in the intent platform mapping.

Initial intent shape:

```yaml
id: notify-response-ready
semantic_event: turn_stop
handler:
  type: command
  script: scripts/notify.py
  title:
    codex: Codex
    claude: Claude Code
  message:
    codex: Response ready
    claude: Response ready
  no_wait: true
  quiet: true
  best_effort: true
platforms:
  codex:
    event: Stop
    timeout: 15
    status_message: Sending notification
    root_var: CODEX_CACHE_PLUGIN_ROOT
    windows_root_var: CODEX_CACHE_PLUGIN_ROOT_WINDOWS
    stdout_policy: empty
  claude:
    event: Stop
    timeout: 35
    async: true
    root_var: CLAUDE_PLUGIN_ROOT
```

Installer behavior:

- If `plugins/<plugin>/hooks/intents/*.yaml` exists, adapters render platform
  hooks from intents.
- Codex generated packages always receive rendered hooks at `hooks/hooks.json`.
- Claude generated packages always receive rendered hooks at `hooks/hooks.json`.
- Source plugin directories must not maintain `hooks/hooks.json`, `hooks/claude/`,
  or `hooks/codex/`.
- Validation checks generated Codex hooks against intent output and still applies
  Codex-specific hook safety checks.

Codex hook templates may use installer-rendered placeholders:

- `{{PLUGIN_NAME}}`
- `{{PLUGIN_VERSION}}`
- `{{MARKETPLACE_NAME}}`
- `{{CODEX_CACHE_PLUGIN_ROOT}}`
- `{{CODEX_CACHE_PLUGIN_ROOT_WINDOWS}}`

Codex hook configs must not use `async: true` or Claude-only variables such as `${CLAUDE_PLUGIN_ROOT}`.
Notification-style Codex hooks must use `--quiet --best-effort` so they do not write non-JSON text to stdout or fail the agent turn when the local desktop notification backend is unavailable. Click-to-focus is platform-specific: Windows uses a detached NotifyIcon listener, macOS requires `terminal-notifier` for reliable click activation, and Linux requires an action-capable notification daemon plus `xdotool` or `wmctrl`.

Claude hook configs may use `async: true`, `Notification`, and
`${CLAUDE_PLUGIN_ROOT}`. These must be generated only for Claude and must never
leak into Codex packages.

## Implementation Phases

### Phase 1: Codex Packaging

- Add `.codex-plugin/plugin.json` for each plugin.
- Replace hand-maintained source `.codex-plugin/plugin.json` files with
  `plugins/plugin-metadata.json` and generate Codex manifests only into
  `.codex/generated/plugins/<plugin>/`.
- Generate ignored `.agents/plugins/marketplace.json` during install.
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
- Generate Claude package folders under `.claude/generated/plugins/`.
- Generate `.claude-plugin/marketplace.json` from `plugins/plugin-metadata.json`.
- Validate generated `.claude-plugin` manifests.
- Preserve current Claude marketplace entry shape while changing sources to generated packages.

### Phase 5: Optional Rule Adapters

- Add Cursor adapter to generate `.mdc` files.
- Add Windsurf adapter only if the skill body can fit its rule size limits.
- Keep generated adapter files out of canonical skill sources unless they are intentionally committed.

### Phase 6: Hook Intent Generation

- Add `plugins/dev-tools/hooks/intents/*.yaml` as canonical hook definitions.
- Add `scripts/hook_intents.py` with a standard-library parser for the controlled
  intent YAML subset and renderers for Codex and Claude.
- Update Codex and Claude adapters to render platform hooks from intents.
- Update validation so generated platform package hooks must match intent output
  when generated packages are present.

### Phase 7: Single-Source Hook Cleanup

- Remove hand-written platform hook JSON from source plugin directories.
- Generate hook JSON only under platform generated package directories.
- Expand intent platform mappings for Cursor/Windsurf only when those platforms
  have a hook/rule surface that can faithfully represent the semantic event.

## Acceptance Criteria

- `python scripts/validate.py --all` passes.
- Codex can discover all four plugins after running the installer-generated `.agents/plugins/marketplace.json`.
- Claude install docs and existing plugin metadata still work.
- No skill content is duplicated for Codex.
- Hook migration is explicit and does not silently reuse Claude-only hook configuration.
- Hook intent files are the canonical source for dev-tools notification hooks.
- Codex generated hook output remains quiet/best-effort and contains no Claude-only fields.

## Open Decisions

- Decision: source plugin directories should not maintain Codex manifests; they
  are generated from `plugins/plugin-metadata.json` during install/package generation.
- Decision: source plugin directories should not maintain Claude manifests; they
  are generated from `plugins/plugin-metadata.json` during install/package generation.
- Decision: platform marketplace files should not be hand-maintained; both
  `.agents/plugins/marketplace.json` and `.claude-plugin/marketplace.json` are
  generated from `plugins/plugin-metadata.json` and ignored by git.
- Whether user-level installs should copy files or create symlinks.
- Whether Cursor/Windsurf adapters are in scope for the first release.
- Whether generated platform hook JSON should be committed or treated as purely
  installer-generated output.
