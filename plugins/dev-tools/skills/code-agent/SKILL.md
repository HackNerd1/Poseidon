---
name: code-agent
description: '主责代码实施：按第一性原理定位落点、复用/封装决策、对齐现有风格后实现并验收。当用户要求实现功能、按任务写代码、修复并落地变更，或 plan 进入代码实施阶段时触发。附带为 plan 提供 planning sub-agent 的 Prompt/验收（见 references/planning-support.md）。触发短语："code-agent"、"实现这个任务"、"按计划写代码"、"code agent prompt"、"验收实现"。不负责派发决策与进度编排（由 plan 负责）。'
---

# Code-Agent Skill — 代码实施（主）与计划支持（附）

## 概述

**主职责：代码实施。** 在动笔前用第一性原理回答「做最小什么、写在哪、复用还是封装、如何验证」，再对齐现有实现完成改动并验收。

**附职责：计划生成支持。** 仅当 `plan` 需要构造/验收 planning sub-agent 时，加载 `references/planning-support.md`；不因此改变本 skill 的主路径。

本 skill 可被用户直接 `/code-agent` 调用，也可被 `plan` 在实施阶段调用。

## 职责边界

| 职责 | 归属 | 参考 |
|------|------|------|
| 定位落点、复用/封装、风格对齐、编码、测试 | **主** | `references/coding-rules.md` |
| 实施 Prompt 模板与结果验收 | **主** | `references/standards.md` |
| Planning sub-agent Prompt / 计划文档验收 | **附** | `references/planning-support.md` |
| 需求澄清、阶段编排、派发决策、进度 checkbox | 非本 skill | `plan` |
| 远端文档同步 | 非本 skill | `doc-sync` |

## 主工作流：代码实施

### Step 0：确认输入

至少具备其一：
- 详细计划中的任务（ID + 描述 + 验收标准），或
- 用户直接给出的可验收实现需求

若验收标准缺失 → 先补 2–3 条二值标准，再实施。

### Step 1：加载编码规则

> **L3 加载**：`references/coding-rules.md`

Read 全文（尤其第一～四章），再继续。

### Step 2：第一性原理四问（强制）

按 `coding-rules.md` 第一节输出简短结论：
- 最小成果 / 落点 / 复用与封装 / 验证方式 / 不做

未完成四问 → **禁止**开始改业务代码。

### Step 3：编码前对齐

按 `coding-rules.md` 第四章清单：
1. Read 同类现有实现
2. Read 同类测试（若有）
3. 扫 lint / 风格配置
4. 确认依赖边界

### Step 4：实施

按四问结论与任务验收标准改代码。构造子 agent prompt 时使用 `references/standards.md` 第二章模板（模板内已引用 coding-rules）。

遵守：
- 只改验收所需
- 落点与风格跟仓
- 核心逻辑补测或约定验证

### Step 5：验收与回报

按 `references/standards.md` 第三章验收。

回报至少包含：
1. 四问结论摘要
2. 修改文件列表（含与预估差异）
3. 验收标准逐条结果
4. 测试 / 验证情况
5. 若来自计划：checkbox 是否已回写

## 附工作流：计划生成支持

仅当调用方明确场景为「总体计划」或「详细计划」时进入：

1. Read `references/planning-support.md`（不要加载 coding-rules，除非同时要实施）
2. 按二.1 / 二.2 构造 planning prompt，或按三.1 验收计划文档
3. 计划文档结构模板仍由 `plan` 加载其自身 references

## 关键规则

1. **实施为主**：默认路径是编码落地；计划支持只在显式请求时加载
2. **先问后写**：四问未完成不得改业务代码
3. **跟仓不跟臆想**：目录、命名、错误处理、测试方式以现有实现为准
4. **复用优于新建**：能扩展现有模块就不平行开树；封装有门槛（见 coding-rules）
5. **验收二值**：每条标准必须可判定通过/不通过
6. **不自动派发**：若由 `plan` 调用，派发确认仍由 `plan` 负责

## 被其他 skill 调用时

| 调用方场景 | 应加载 |
|------------|--------|
| 代码实施 / 验收实现 | `coding-rules.md` + `standards.md` |
| 总体计划 / 详细计划 Prompt 或验收 | **仅** `planning-support.md` |

调用方（如 `plan`）应说明场景，并使用 `/code-agent` 或 Skill tool 加载本 skill。
