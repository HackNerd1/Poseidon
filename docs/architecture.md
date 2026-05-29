# Poseidon 架构文档

> Claude Code 插件大仓 —— 覆盖开发提效、生活自动化、软考备考等多场景。

---

## 一、Claude Code Skill 标准格式

### 1.1 什么是 Skill

Skill 是 Claude Code 的插件机制，通过声明式配置让 Claude 获得专业领域能力。每个 Skill 由一个 `SKILL.md` 文件定义，遵循 [Agent Skills 开放标准](https://agentskills.io)。

### 1.2 目录结构

```
skill-name/
├── SKILL.md          # 必需 — 技能定义文件
├── scripts/          # 可选 — 确定性计算脚本（Python/Bash）
├── references/       # 可选 — 参考文档，按需加载到上下文
├── assets/           # 可选 — 模板等输出用文件
└── LICENSE.txt       # 可选
```

### 1.3 SKILL.md 格式

#### YAML Frontmatter（必需）

```yaml
---
name: skill-name           # 小写+连字符，3-64 字符，字母数字开头结尾
description: 技能描述       # 最长 1024 字符，说明做什么和何时触发
---
```

**完整 Frontmatter 字段：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 技能名和 `/` 斜杠命令标识符 |
| `description` | string | 是 | Claude 自动发现技能的依据，含触发条件 |
| `context` | string | 否 | 设为 `fork` 则在独立子 agent 中运行 |
| `agent` | string | 否 | 子 agent 类型（需 `context: fork`） |
| `allowed-tools` | string | 否 | 技能运行时免确认的工具列表 |
| `model` | string | 否 | 模型覆盖：`haiku` / `sonnet` / `opus` / `inherit` |
| `disabel-model-invocation` | boolean | 否 | 禁止 Claude 自动触发此技能 |
| `user-invocable` | boolean | 否 | 设为 `false` 隐藏 `/` 菜单项 |
| `paths` | string/list | 否 | Glob 模式，限制技能自动激活的文件范围 |
| `hooks` | object | 否 | 生命周期钩子（作用域限此技能） |
| `shell` | string | 否 | `bash`（默认）或 `powershell` |
| `argument-hint` | string | 否 | 自动补全提示 |
| `arguments` | string/list | 否 | 命名位置参数，用于 `$name` 替换 |

#### Body（Markdown）

```markdown
# 技能标题

## 概述
技能用途和能力边界。

## 核心职责
1. 职责 1
2. 职责 2

## 工作流 / 分析流程
1. 第一步
2. 第二步

## 输入要求
- 数据格式
- 必需字段

## 输出格式
- 结果结构

## 质量标准 / 关键规则
- 规则 1
- 规则 2

## 边界情况
- 情况 1：处理方式

## 限制
- 已知约束
- 什么时候不该用此技能
```

### 1.4 三级渐进式加载

| 级别 | 内容 | 加载时机 | Token 预算 |
|------|------|----------|------------|
| L1 | YAML frontmatter（name + description） | 会话启动 | ~100 |
| L2 | SKILL.md body | 技能触发时 | <5000 推荐 |
| L3 | 捆绑资源（scripts/、references/、assets/） | 按需引用 | 无限制 |

### 1.5 安装位置

| 类型 | 路径 | 作用域 |
|------|------|--------|
| 个人技能 | `~/.claude/skills/` | 所有项目 |
| 项目技能 | `.claude/skills/` | 单个项目（版本控制） |
| 插件 | 插件市场安装 | 全局 |

---

## 二、Skill 架构设计模式

### 2.1 Claude-Native Loop Controller

基于 state.json 的调度模式，Claude 自身充当任务调度器：

```
SKILL.md (Claude-Native loop controller)
  ├── 读取 state.json — 恢复/确定当前进度
  ├── 选择下一项工作 — 按优先级和依赖决策
  ├── 读取 reference/*.md 模板并填充参数
  ├── 通过 Agent tool 派发子 agent — 并发处理独立任务
  └── 验证 state.json 中的结果
```

**职责分工：**

| 组件 | 擅长 | 不擅长 |
|------|------|--------|
| **SKILL.md (Claude)** | 理解上下文、决策调度、推理判断 | 确定性计算 |
| **Agent tool** | 代码理解、推理、生成、多步任务 | 需要全局状态的协作 |
| **Bash / Python** | 确定性计算、LSP 调用、hash、chunk 边界、文件渲染 | 需要判断和推理 |

### 2.2 Worker Contract 模式

每个 `reference/*.md` 是一个边界清晰的 worker contract：
- 定义单一子任务的输入/输出契约
- 子 agent 只读自己需要的 reference
- 结果通过文件系统或 state.json 回传

### 2.3 插件目录约定

```
plugin-name/
├── skills/                    # 技能集合
│   ├── skill-one/
│   │   └── SKILL.md
│   └── skill-two/
│       └── SKILL.md
├── agents/                    # 可选 — 自定义 sub-agents
├── references/                # 共享参考文档
├── scripts/                   # 共享脚本
├── assets/                    # 模板和静态文件
└── README.md                  # 插件说明
```

---

## 三、Poseidon 大仓架构

### 3.1 仓库布局

```
Poseidon/
├── README.md
├── docs/
│   └── architecture.md        # 本文档
├── plugins/                   # 插件根目录
│   └── ruankao/               # 软考备考插件
│       ├── skills/
│       │   ├── write-paper/   # 论文从零写作
│       │   │   ├── SKILL.md
│       │   │   ├── references/   # 写作技巧、范文、PRD、方法论
│       │   │   └── scripts/      # count_chars.py
│       │   ├── enhance-paper/ # 论文优化
│       │   │   ├── SKILL.md
│       │   │   ├── references/   # 写作技巧、范文、PRD
│       │   │   └── scripts/      # count_chars.py
│       │   ├── teleprompter/  # 帮记词生成
│       │   │   └── SKILL.md
│       │   └── tts/           # 文本转语音
│       │       ├── SKILL.md
│       │       └── scripts/      # extract_body, tts_edge, tts_tencent
│       └── README.md
│   └── dev-tools/             # 开发提效插件（预留）
│   └── life-automation/       # 生活自动化插件（预留）
└── .claude/
    └── settings.local.json
```

### 3.2 设计原则

1. **按场景分插件**：每个插件对应一个独立的业务场景（软考、开发、生活），互不耦合
2. **Skill 自包含**：每个 skill 目录独立携带自己的 `references/` 和 `scripts/`，可直接安装到 `.claude/skills/` 下使用，无跨 skill 耦合
3. **Skill 即入口**：每个 `SKILL.md` 是唯一的 Claude 入口点，通过 `description` 字段实现自动发现
4. **确定性计算外置**：字数统计、正文提取等纯计算逻辑用 Python 脚本；推理决策保留在 SKILL.md 工作流中
5. **L3 按需加载**：reference 文档在 SKILL.md 工作流中按步骤显式引用，不预加载

### 3.3 插件安装

通过 Claude Code 标准插件机制安装：

```bash
# 注册 Marketplace（首次）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon

# 安装插件
/plugin install ruankao@poseidon

# 或本地路径安装
/plugin install ./plugins/ruankao
```

---

## 四、Skill 编写最佳实践

### DO
- 用第二人称（"你将…"、"按以下流程执行"）
- 包含具体的输入/输出示例
- 为另一个 Claude 实例而写，不是为人而写
- 控制在 500 行以内，细节放入 `references/`
- `description` 包含触发短语

### DON'T
- 写模糊的一行文（"帮助完成任务"）
- 把所有信息塞进一个文件
- 包含安装说明、测试步骤等面向人类的内容
- 写抽象的理论指导
- 重复 Claude 已知的常识

---

## 五、Agent 格式速查

插件中可选的 Agent 文件格式（`agents/*.md`）：

```yaml
---
name: agent-name
description: Use this agent when... Examples: <example>...</example>
model: inherit
color: blue
tools: ["Read", "Write", "Grep"]
---

你是一个专门处理 [X] 的 agent。

**核心职责：**
1. 职责 1

**分析流程：**
1. 步骤 1

**输出格式：**
- 结构说明
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 3-50 字符，小写+连字符 |
| `description` | 是 | 含 `<example>` 触发示例 |
| `model` | 是 | `inherit` / `sonnet` / `opus` / `haiku` |
| `color` | 是 | `blue` / `cyan` / `green` / `yellow` / `magenta` / `red` |
| `tools` | 否 | 工具列表，省略或 `["*"]` 为全权限 |

---

## 六、参考资料

- [Agent Skills 开放标准](https://agentskills.io)
- [Claude Plugins 官方仓库](https://github.com/anthropics/claude-plugins-official)
- [Claude Code Skills 最佳实践](https://github.com/shanraisshan/claude-code-best-practice)
