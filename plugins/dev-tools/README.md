# dev-tools

**开发提效插件 —— 覆盖代码实施、代码审查、需求计划、PR 创建、变更集生成、文档同步、README 生成、知识提取与诊断调试。**

技能按开发流程串联：`plan` 澄清需求并拆分任务，`code-agent` 落地实现，`code-review` 审查变更，`gen-changeset` 生成变更集/发版说明，`pr` 提交 PR/MR；`debugger`、`doc-sync`、`extra-knowledge`、`gen-readme` 覆盖独立场景。

## 技能一览

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `plan` | 从需求到实施：澄清阻塞未知数 → 需求文档 → 总体/详细计划 → 分批派发实施；支持 local / feishu / notion 存储 | 提供需求描述或文档链接，说“帮我做计划”“拆分任务” |
| `code-agent` | 主责代码实施：按第一性原理定位落点、做复用/封装决策、对齐现有风格后实现并验收 | “实现这个任务”“按计划写代码”，或由 `plan` 派发 |
| `code-review` | 第一性原理代码审查：正确性、冗余设计、文档-代码一致性、架构边界、PR 审查 | “review code”“代码审查”“检查暂存变更” |
| `pr` | 创建 PR/MR：自动识别 GitHub / GitLab / Gitea，本地起草描述，确认后用 gh / glab / tea 提交 | “create PR”“提交 PR”“open merge request” |
| `gen-changeset` | 生成 changeset / 变更说明：识别 Changesets、release-please、semantic-release 等发版工具，按公开影响选择 major/minor/patch，写 WHAT/WHY/HOW 摘要与大版本迁移说明，并用脚本校验 | “生成 changeset”“加变更说明”“写 changelog”“该升哪个版本” |
| `debugger` | 诊断式 Debug：日志分析、白屏/渲染异常、数据不符预期等运行时问题排查 | 粘贴日志或描述 Bug 现象 |
| `doc-sync` | 本地 Markdown 与飞书 / Notion 同步：创建、更新、拉取远端文档，维护 doc-map | “同步飞书文档”“同步 Notion” |
| `extra-knowledge` | 代码仓库知识提取：项目扫描与模块映射 → 并行模块分析 → 输出知识报告到 `.Poseidon/extra-knowledge/` | “从这个仓库提取知识”“分析值得学习的设计” |
| `gen-readme` | 生成/改写/审查 README：按仓库事实选 library / cli / app / monorepo / internal-service 模板，可选 banner、图标、图表，最后用脚本审计 | “写 README”“完善 README”“README 审查” |

## 安装

前置条件：Python 3 与 `git`；使用 Claude Code 或 Codex 插件流程时需已安装对应 CLI。

```bash
git clone https://github.com/HackNerd1/Poseidon.git
cd Poseidon
python3 scripts/install.py --platform claude --scope user --plugin dev-tools
```

安装器会生成 `.claude/generated/plugins/dev-tools/` 与 marketplace 清单，再调用 `claude plugin install` 完成注册。把 `--platform` 换成 `codex` 或 `cursor` 可装到其他平台；`--scope repo` 安装到当前项目而非用户级目录。

## 使用

技能默认可作为斜杠命令调用，也可以直接用自然语言描述任务触发：

```text
/plan 为「支持多城市岗位搜索」制定实施计划
/code-review
/gen-readme 更新本仓库根 README
```

链式使用时，`plan` 会调用 `code-agent` 实施、调用 `doc-sync` 同步计划文档；`code-agent` 的实现结果可以交给 `code-review` 审查，再交给 `pr` 提交。

## Hooks 与桌面通知

| 事件 | 说明 |
|------|------|
| `Stop` | Claude 响应完成 → 桌面通知 |
| `PreToolUse` → `AskUserQuestion` | Claude 向用户提问 → 即时弹出通知 |
| `Notification` → `permission_prompt` | Claude 需要工具权限审批 → 即时弹出通知 |
| `Notification` → `idle_prompt` | Claude 空闲等待输入（约 60 秒延迟）→ 桌面通知 |

通知会尽量捕获发送时的前台目标，点击后回到该目标。Windows 使用 NotifyIcon 监听点击并恢复窗口；macOS 优先用 `terminal-notifier -execute` 执行聚焦脚本，未安装时只能显示通知、无法可靠处理点击；Linux 在 X11 下用 `notify-send --action` 配合 `xdotool` / `wmctrl` 激活窗口，Wayland 或缺少工具时退化为普通通知。

配置只维护意图文件：

- 源码：`plugins/dev-tools/hooks/intents/*.yaml`
- 生成物：各平台包内的 `hooks/hooks.json`，由 `scripts/install.py` 渲染

Codex 通知 hook 使用 `--quiet --best-effort`，避免普通日志污染 Codex hook 的 stdout 协议，并在本机通知不可用时不影响对话。

## 平台支持

| 平台 | 技能 | 通知 hooks |
|------|------|------------|
| Claude Code | 插件包 `.claude/generated/plugins/dev-tools/` | 支持 |
| Codex | 插件包 `.codex/generated/plugins/dev-tools/` | 支持 |
| Cursor | 复制到 `.cursor/skills/` | 不支持（安装器只复制技能） |

## 许可证

[MIT License](../../LICENSE)，Copyright (c) 2026 HackNerd1。
