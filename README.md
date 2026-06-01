# Poseidon

Claude Code 插件大仓，覆盖开发提效、算法学习、简历准备、软考备考等多场景。

## 安装

### 方式一：添加 Marketplace 后安装（推荐）

首次使用需注册本仓库为第三方 Marketplace，之后即可浏览和安装其中的插件：

```
# 1. 注册 Marketplace
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon

# 2. 安装插件
/plugin install dev-tools@poseidon
/plugin install ruankao@poseidon
/plugin install algo-coach@poseidon
/plugin install resume@poseidon
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
/plugin install ./plugins/resume
```

## 插件

| 插件 | 路径 | 场景 |
|------|------|------|
| [dev-tools](./plugins/dev-tools/) | `plugins/dev-tools/` | 开发提效 — Debug 诊断、代码审查、桌面通知 |
| [algo-coach](./plugins/algo-coach/) | `plugins/algo-coach/` | 算法学习 — LeetCode 刷题、知识点关联、解法优化 |
| [resume](./plugins/resume/) | `plugins/resume/` | 简历与面试 — 项目提取、简历生成、格式转换、面试准备 |
| [ruankao](./plugins/ruankao/) | `plugins/ruankao/` | 软考系统分析师论文备考 — 论文写作、优化、帮记词、TTS 音频合成 |

### dev-tools 技能

| 技能 | 说明 |
|------|------|
| `code-review` | 代码审查 — 检查暂存/未暂存变更、架构对齐、最佳实践建议 |
| `debugger` | 诊断调试 — 日志分析、白屏/渲染异常、数据不匹配等运行时问题排查 |

### dev-tools Hooks

| Hook | 事件 | 说明 |
|------|------|------|
| `Stop` | Claude 响应完成 | 自动发送桌面通知 |

配置位置：`plugins/dev-tools/hooks/hooks.json`，安装插件后自动生效。

### algo-coach 技能

| 技能 | 说明 |
|------|------|
| `init-problem` | 根据 LeetCode 链接初始化算法题文件，自动归类到题型目录 |
| `link-knowledge` | 为算法题关联 hello-algo.com 知识点并添加解题思路 |
| `optimize-solution` | 分析算法解法的可优化点，生成优化版本并标注改进原因 |

### resume 技能

| 技能 | 说明 |
|------|------|
| `extract-project` | 从 Git 仓库提取项目经验，生成符合 STAR/SARL 法则的简历文档 |
| `create-resume` | 交互式创建完整简历，支持 JSON 导入和 JD 关键词匹配 |
| `convert-md` | 使用 Resumx 将 Markdown 简历转换为 PDF、HTML、DOCX、PNG 等格式 |
| `prep-interview` | 从简历提取技术栈与项目经验，生成结构化面试准备目录 |

### ruankao 技能

| 技能 | 说明 |
|------|------|
| `write-paper` | 论文写作 |
| `enhance-paper` | 论文优化 |
| `teleprompter` | 帮记词生成 |
| `tts` | TTS 音频合成 |

## 架构

详见 [docs/architecture.md](./docs/architecture.md)。
