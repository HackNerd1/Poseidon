# Dev-Tools 插件

开发提效工具集，包含诊断调试、代码审查、PR/MR 创建和桌面通知。

## Skills

| Skill | 说明 | 触发场景 |
|-------|------|----------|
| `debug` | 诊断式 Debug 工作流 | 导入日志分析 Bug、白屏/渲染异常、数据不符预期等运行时问题排查 |
| `code-review` | 结构化代码审查 | 审查暂存/未暂存变更、文档-代码一致性、架构合规检查、PR 审查 |
| `pr` | 渐进式 PR/MR 创建 | 自动检测仓库平台（GitHub/GitLab/Gitea），本地起草 PR 描述，支持流程图/场景视图/手工测试用例，用户确认后通过 gh/glab/tea 提交 |
| `plan` | 渐进式需求分析与实施计划 | 从模糊需求到可执行计划的完整工作流：需求澄清（100分制评分）→ 需求文档生成 → 总体计划（分阶段）→ 详细任务拆分（TODO跟踪）→ 分批派发子agent实施 |

## Hooks

| 事件 | 说明 |
|------|------|
| `Stop` | Claude 响应完成 → 桌面通知 |
| `PreToolUse` → `AskUserQuestion` | Claude 向用户提问 → 即时弹出通知 |
| `Notification` → `permission_prompt` | Claude 需要工具权限审批 → 即时弹出通知 |
| `Notification` → `idle_prompt` | Claude 空闲等待输入（~60s 延迟）→ 桌面通知 |

> 通知会尽量在发送时捕获当前前台目标，并在点击通知时回到该目标。Windows 使用 NotifyIcon 监听点击并恢复窗口；macOS 优先使用 `terminal-notifier -execute` 执行聚焦脚本回到捕获到的 app/window，未安装 `terminal-notifier` 时只能通过 `osascript` 显示通知且无法可靠处理点击；Linux 在 X11 下使用 `notify-send --action` 配合 `xdotool`/`wmctrl` 激活捕获到的窗口，Wayland 或缺少工具时退化为普通通知。

配置位置：

- 源码只维护 `hooks/intents/*.yaml`
- Claude/Codex 的 `hooks/hooks.json` 都由仓库安装器生成到对应平台包中

Codex 通知 hook 使用 `--quiet --best-effort`，避免普通日志污染 Codex hook stdout 协议，并在本机通知不可用时不阻断对话。

## 安装

```bash
# 通过 Marketplace（推荐）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon
/plugin install dev-tools@poseidon

# 或本地路径安装
/plugin install ./plugins/dev-tools
```
