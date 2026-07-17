---
name: code-agent
description: '为 planning/code 子 agent 提供 Prompt 模板、开发规范与结果验收。当需要构造 sub-agent prompt、按规范写代码与测试、验收子 agent 产出，或由 plan skill 在计划生成/代码实施阶段显式调用时使用。触发短语："code-agent"、"code agent prompt"、"验收子 agent"、"planning prompt 模板"。不负责派发决策与进度编排（由 plan 负责）。'
---

# Code-Agent Skill — 计划生成与代码实施的 Agent 规范

## 概述

为子 agent 提供：**Agent 类型选择、Planning/Code Prompt 模板、开发规范、结果验收**。

本 skill 可被 `plan` 等其他 skill 通过 `/code-agent` 或 Skill tool 调用；也可在独立实施任务时直接使用。

## 何时加载哪一章

> **L3 加载**：`references/standards.md`

| 场景 | 加载章节 |
|------|----------|
| 生成总体计划 | 二.1 + 五.1 |
| 生成详细计划 | 二.2 + 五.1 |
| 派发代码实施 | 三 + 四 + 五.2 / 五.3 |
| 仅查开发规范 | 四 |
| 仅做结果验收 | 五 |

## 工作流

### Step 1：加载规范

Read `references/standards.md`（按上表只取需要的章节，避免整文件灌入上下文）。

### Step 2：构造 Prompt 或执行验收

- **计划生成**：按第二章模板构造 planning sub-agent prompt；完成后按 5.1 验收
- **代码实施**：按第三章模板构造 code agent prompt，遵守第四章开发规范；完成后按 5.2 验收；不通过按 5.3 处理

### Step 3：回报

完成后报告：
1. 使用的模板章节（2.1 / 2.2 / 3.x）
2. 派发时：prompt 是否已按模板构造
3. 验收时：checklist 逐条通过/失败项
4. 失败时的处理建议（补充 / 重派 / 人工介入）

## 关键规则

1. **规范外置**：Prompt、注释/测试/风格要求、验收标准以 `references/standards.md` 为准
2. **计划模板仍属 plan**：`overall-plan-template.md` / `plan-template.md` 仍由 `plan` skill 加载；本 skill 只提供 sub-agent prompt 与验收
3. **不自动派发**：构造 prompt 后由调用方（通常是 `plan`）在用户确认后派发
4. **验收二值**：每条验收标准必须可判定通过/不通过

## 被其他 skill 调用时

调用方（如 `plan`）应：
1. 通过 `/code-agent` 或 Skill tool 加载本 skill
2. 说明场景（总体计划 / 详细计划 / 代码实施 / 验收）
3. 不要再读取 `plan/references/code-execution-standards.md`（已迁移至此）
