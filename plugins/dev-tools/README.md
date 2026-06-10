# Dev-Tools 插件

开发提效工具集，包含诊断调试、代码审查和桌面通知。

## Skills

| Skill | 说明 | 触发场景 |
|-------|------|----------|
| `debug` | 诊断式 Debug 工作流 | 导入日志分析 Bug、白屏/渲染异常、数据不符预期等运行时问题排查 |
| `code-review` | 结构化代码审查 | 审查暂存/未暂存变更、文档-代码一致性、架构合规检查、PR 审查 |

## Hooks

| Hook | 事件 | 说明 |
|------|------|------|
| `Stop` | Claude 响应完成 | 自动发送桌面通知 |
| `PostToolUse` → `AskUserQuestion` | Claude 向用户提问 | 弹出通知提醒用户需要回复 |

> 通知支持点击后回到 Claude Code 窗口（Windows 原生支持，macOS 需安装 `terminal-notifier`，Linux 通过 `notify-send --action` 实现）。

配置位置：`hooks/hooks.json`，安装插件后自动生效。

## 安装

```bash
# 通过 Marketplace（推荐）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon
/plugin install dev-tools@poseidon

# 或本地路径安装
/plugin install ./plugins/dev-tools
```
