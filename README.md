# Poseidon

Claude Code 插件大仓，覆盖开发提效、生活自动化、软考备考等多场景。

## 安装

### 方式一：添加 Marketplace 后安装（推荐）

首次使用需注册本仓库为第三方 Marketplace，之后即可浏览和安装其中的插件：

```
# 1. 注册 Marketplace
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon

# 2. 安装插件
/plugin install dev-tools@poseidon
/plugin install ruankao@poseidon
```

> **Windows 用户注意**：若 `/plugin marketplace add` 不可用（官方 Marketplace 在 Windows 上未预注册），需先在 `~/.claude/settings.json` 中添加：
> ```json
> {
>   "extraKnownMarketplaces": {
>     "poseidon": {
>       "source": "https://github.com/HackNerd1/Poseidon"
>     }
>   }
> }
> ```

### 方式二：本地安装

```bash
git clone https://github.com/HackNerd1/Poseidon.git
cd Poseidon

# 在 Claude Code 会话中安装
/plugin install ./plugins/dev-tools
/plugin install ./plugins/ruankao
/plugin install ./plugins/algo-coach
```

## 插件

| 插件 | 路径 | 场景 |
|------|------|------|
| [dev-tools](./plugins/dev-tools/) | `plugins/dev-tools/` | 开发提效 — Debug 诊断、日志分析、代码审查辅助、桌面通知 |
| [ruankao](./plugins/ruankao/) | `plugins/ruankao/` | 软考系统分析师论文备考 — 论文写作、优化、帮记词生成、TTS 音频合成 |

### dev-tools 技能

| 技能 | 说明 |
|------|------|
| `debugger` | 诊断调试 — 日志分析、白屏/渲染异常、数据不匹配等运行时问题排查 |
| `code-review` | 代码审查 — 暂存/未暂存变更检查、架构对齐、最佳实践建议 |

### dev-tools Hooks

| Hook | 事件 | 说明 |
|------|------|------|
| `Stop` | Claude 响应完成 | 自动发送桌面通知，无需手动调用 |

配置位置：`plugins/dev-tools/hooks/hooks.json`，安装插件后自动生效。

### ruankao 技能

| 技能 | 说明 |
|------|------|
| `write-paper` | 论文写作 |
| `enhance-paper` | 论文优化 |
| `teleprompter` | 帮记词生成 |
| `tts` | TTS 音频合成 |

## 架构

详见 [docs/architecture.md](./docs/architecture.md)。
