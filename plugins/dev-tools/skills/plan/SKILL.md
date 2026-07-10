---
name: plan
description: '从需求到实施的渐进式计划工作流。当用户提供需求描述/文档链接要求制定实施计划、澄清需求、拆分任务时触发。适用场景：需求澄清与阻塞未知数识别、需求文档生成、总体计划制定、详细任务拆分、分批派发子 agent 实施。支持本地 Markdown、飞书 CLI、Notion CLI 三种文档存储方式。触发短语："帮我做计划"、"plan this"、"分析需求"、"拆分任务"、"制定实施方案"、"clarify requirements"、"create implementation plan"。'
---

# Plan Skill — 从需求到实施的渐进式计划工作流

## 概述

你将帮助用户将模糊需求逐步转化为可执行的实施计划。核心原则：**先澄清、回归第一性原理、再计划、后派发**。流程覆盖：输入验证 → 需求探讨 → 需求文档 → 总体计划 → 详细计划 → 派发实施 → 循环迭代。

你充当 Claude-Native Loop Controller：读取参考模板、评估阻塞未知数、调度子 agent 执行任务、通过计划文档中的 Markdown checkbox 跟踪进度。

默认输出原则：
- **默认极简**：只保留推进决策和实施所必需的信息
- **不要为了拆分而拆分**：同一条最小交付链路默认合并

文档写入原则：
- `local`：直接写入 `docs/requirements/`
- `feishu` / `notion`：始终先写本地副本，再按对应 workflow 同步远端

## 输入要求

用户需提供：
1. **需求描述**（必需）：文档链接、自然语言描述、或本地文件路径
2. **文档存储方式**（可选，默认 `local`）：`local`（本地 Markdown）、`feishu`（飞书 CLI）或 `notion`（Notion CLI）
3. **文档路径**（可选）：默认 `docs/requirements/`

## 工作流

### Step 0：验证输入

1. **需求描述**是否提供？未提供 → 提示：
   > 请提供需求信息：文档链接、自然语言描述、或本地文件路径。

2. **存储方式**：未声明 → 默认 `local`，告知用户。
   - 用户选择 `feishu` → Read `references/feishu-workflow.md` 第二、五章，验证 CLI 可用（`which feishu`），初始化 `.Poseidon/feishu/` 目录和 `doc-map.json`
   - 用户选择 `notion` → Read `references/notion-workflow.md` 第一、二、五章，验证 CLI 可用（`which ntn`），初始化 `.Poseidon/notion/` 目录和 `doc-map.json`
     - 用户必须显式提供 Notion 页面或 database 的 URL / ID；未提供则提示补充

3. **存储路径**：确保目标目录存在（`local` 则 `mkdir -p docs/requirements/`）。

验证通过后确认摘要并进入 Step 1。

### Step 1：探讨需求（需求澄清）

> **L3 加载**：`references/requirement-clarification-guide.md`

#### 1.1 加载澄清指南

Read `references/requirement-clarification-guide.md`，获取：
- 六维评估框架与阻塞未知数判定规则（第二章）
- 模糊词翻译表（第三章）
- 提问模板（第四章）
- 快速检查卡（第六章）

#### 1.2 首次评估

按六维框架做首次诊断，识别：
- 已明确的信息
- 会阻塞方案、范围、验收或实施顺序的未知数
- 可延后到实施阶段再确认的未知数

如有帮助，可给出轻量评分作为沟通辅助，但**不得**把总分作为进入计划阶段的硬门槛。

#### 1.3 联网补充（可选）

需求领域不常见时搜索网络获取背景知识，交叉比对发现遗漏点。

#### 1.4 多轮提问

- 每轮 **2-3 个问题**，优先解决会阻塞决策的未知数
- 尽量给出选项（A/B/C），量化模糊词，每轮结束复述理解
- **上限 10 轮**。超过后仍有未知数时，区分：
  - 会阻塞当前阶段计划的未知数 → 明确列为开放问题或先做最小验证
  - 不阻塞当前阶段的未知数 → 记录后继续进入计划

#### 1.5 更新与总结

每轮更新“阻塞未知数状态”，必要时附带轻量评分变化（如"45 → 65，+20"）作为辅助说明。满足以下条件之一后，按指南第七章模板生成澄清记录并按当前存储方式落盘/同步：

- 当前阶段所需的关键决策信息已齐备
- 剩余未知数不会改变当前阶段方案，只影响后续细化
- 可通过单个最小验证任务吸收剩余高风险未知数

告知用户阻塞未知数结论和记录路径，确认后进入 Step 2。

### Step 2：更新/创建需求文档

> **L3 加载**：`references/requirement-doc-template.md`

#### 2.1 判断是否需要更新

检查是否已有需求文档。如有 → 对比差异，询问更新（A: 更新 / B: 保留 / C: 新建版本）。如无 → 直接创建。

#### 2.2 生成需求文档

Read `references/requirement-doc-template.md`，按模板结构填充：
1. 背景与目标
2. 功能需求（核心功能 + 输入/输出 + 交互流程）
3. 非功能需求（性能 / 安全 / 兼容性）
4. 验收标准（checkbox，可独立验证）
5. 范围边界（范围内 + 范围外）
6. 约束与假设

生成后按模板质量检查清单自检，并按当前存储方式落盘/同步。

确认后进入 Step 3。

### Step 3：生成总体计划

> **L3 加载**：`references/overall-plan-template.md`、`references/code-execution-standards.md`（planning sub-agent prompt 模板）

#### 3.1 评估是否需要总体计划

改动很小（单文件修改、配置变更、Bug 修复、预估 ≤3 个任务）→ 跳过，告知用户后直接进入 Step 4。

否则进入 3.2。

#### 3.2 派发 planning sub-agent 生成总体计划

Read `references/overall-plan-template.md` 了解文档结构。
Read `references/code-execution-standards.md` 第二章获取 planning sub-agent prompt 模板。

按模板构造 prompt，包含：需求文档路径、澄清记录路径、架构约束。总体计划的第一性原理、阶段划分、最小可行性验证和极简输出规则统一以 `code-execution-standards.md` 2.1 与 `overall-plan-template.md` 为准。

使用 **Agent tool** 派发 `general-purpose` 类型子 agent：

```
Agent tool:
  description: "Generate overall plan for <feature-name>"
  prompt: <按 code-execution-standards.md 第二章模板构造>
  subagent_type: "general-purpose"
```

#### 3.3 验证与 TODO 创建

子 agent 完成后，按 `code-execution-standards.md` 5.1 节验收。

通过后将每个阶段的宏观任务写入总体计划文档中的 checkbox 列表。

完成后告知用户阶段数量，确认后进入 Step 4。

### Step 4：生成详细计划

> **L3 加载**：`references/plan-template.md`、`references/code-execution-standards.md`、项目架构约束文档

#### 4.1 搜索架构约束

搜索项目架构约束（按优先级）：
1. 用户指定的路径
2. `docs/architecture.md`
3. `CLAUDE.md`
4. `README.md` 中架构部分

未找到 → 询问用户。找到 → 提取关键约束（技术栈、目录约定、命名规范、测试要求）。

#### 4.2 派发 planning sub-agent 生成详细计划

Read `references/plan-template.md` 了解文档结构。
Read `references/code-execution-standards.md` 第二章获取 planning sub-agent prompt 模板。

按模板构造 prompt，包含：需求文档路径、总体计划路径（如有）、澄清记录路径、架构约束。详细计划的任务粒度、第一性原理、最小可行性验证、图示、测试策略和“未来导向”约束统一以 `code-execution-standards.md` 2.2 与 `plan-template.md` 为准。

使用 **Agent tool** 派发 `general-purpose` 类型子 agent：

```
Agent tool:
  description: "Generate detailed plan for <feature-name> Phase <N>"
  prompt: <按 code-execution-standards.md 第二章模板构造>
  subagent_type: "general-purpose"
```

如果多个阶段可并行规划，可同时派发多个 planning sub-agent（如 Phase 2 和 Phase 3 同时规划）。

#### 4.3 验证与 TODO 创建

子 agent 完成后，按 `code-execution-standards.md` 5.1 节验收。

通过后将每个叶子任务写入详细计划文档中的 checkbox 列表；后续执行状态直接回填文档，不依赖外部 TODO API。

完成后告知用户任务数、依赖关系和并行可能性，进入 Step 5。

### Step 5：询问派发实施

> **L3 加载**：`references/dispatch-strategies.md`、`references/code-execution-standards.md`

Read `references/dispatch-strategies.md`，了解四种派发模式和选择决策树。
Read `references/code-execution-standards.md` 第三章，获取 Code Agent Prompt 模板和开发规范。

基于当前就绪任务（依赖已满足）给出推荐方式：

> 当前批次（Phase <N>）计划已就绪，是否开始实施？
>
> 1. **串行派发** — 按依赖顺序逐个执行
> 2. **并行派发** — 无依赖任务同时执行（≤5 个）
> 3. **仅派发当前任务** — 只执行下一个就绪任务
> 4. **暂不实施** — 保留计划
>
> 推荐：<基于决策树的推荐方式>

**用户确认后才派发**，不自动派发。

派发时使用 **Agent tool**（`general-purpose` 类型），按 `code-execution-standards.md` 第三章构造 prompt，并按第五章与 `dispatch-strategies.md` 3.3 节验收；不通过则要求补充。

### Step 6：更新与循环

#### 6.1 任务完成后更新

每个子 agent 完成后，按 `code-execution-standards.md` 5.2 节验收：
- 验收标准逐条达成 → 标记 `[x]`
- 注释/测试/风格不通过 → 要求补充后重新提交

通过后：
1. 更新详细计划文档：标记完成项 `[x]`
2. 更新总体计划文档：阶段内全部完成则标记阶段完成
3. 以计划文档中的 checkbox 为唯一进度事实源

如果存储方式为 `notion`，且当前文档需要更新已有页面内容，按 `notion-workflow.md` 三.3 / 四.2 节执行：
1. 优先保留本地 Markdown 为事实源
2. 用户必须显式提供目标页面 URL / ID
3. 用 `ntn pages edit` 覆盖页面正文
4. 必要时回读校验

子 agent 失败时按 `dispatch-strategies.md` 3.4 节处理（重试/调整/人工介入）。

#### 6.2 询问是否继续

当前批次全部完成后：

> Phase <N> 已完成（<done>/<total>）。是否继续？
> 1. 生成下一批次计划 → 回到 Step 4
> 2. 调整后生成 → 描述调整，回到 Step 4
> 3. 全部完成 → 输出总结
> 4. 暂停 → 保存进度

#### 6.3 输出总结

全部阶段完成时输出结构化总结：

```
📋 计划总结 — <功能名称>
├── 📝 需求澄清：<阻塞未知数结论> | <path>
├── 📄 需求文档：<path>
├── 🗺️ 总体计划：<N> 阶段 <M> 任务 | <path>
├── 📐 详细计划：Phase <current> | <path>
├── ✅ 已完成：<done>/<total> 任务
├── 🔜 下一阶段：<next phase or "无">
└── 📚 架构约束来源：<path or "通用最佳实践">
```

## 关键规则

1. **先澄清再计划**：关键决策信息齐备，或剩余未知数已被隔离为开放问题/最小验证任务后进入计划阶段
2. **每轮 2-3 个问题**：给选项减少输入；量化模糊词
3. **渐进式加载**：每步开始时显式 Read 对应 reference，不过早加载
4. **计划文档可追溯**：每个文档关联上一步文档，形成完整链
5. **进度以文档为准**：计划文档中的 checkbox 是默认进度事实源
6. **架构约束优先**：未找到约束文档时主动询问
7. **计划与实施规范外置**：计划生成、模板约束、开发规范、验收标准以 `code-execution-standards.md` 和各 template 为准
8. **子 agent 不自动派发**：必须用户确认
9. **进度持久化**：所有文档和进度记录写入文件系统，支持中断恢复
10. **每步确认**：Step 1→2、Step 3→4、Step 5 派发、Step 6 循环均需确认
11. **远端文档本地优先**：`feishu` / `notion` 都必须先写本地副本，再同步到云端
12. **Notion 显式目标**：Notion 模式下必须由用户显式提供页面或 database 的 URL / ID
13. **Notion 只负责内容**：Notion workflow 默认只负责文档内容创建、更新、读取，不负责模板、项目结构或归档策略

## 边界情况

- **需求是代码**（如"重构 utils/helper.js"）→ 跳过 Step 1-2，直接 Step 3，以代码文件为需求来源
- **用户中途修改需求** → 回到 Step 1 重新评估，增量更新现有文档
- **架构约束与需求冲突** → 明确指出冲突，让用户决策
- **飞书 CLI 不可用** → 降级为 local，告知用户。详见 `feishu-workflow.md` 第五章
- **飞书文档冲突** → 按 `feishu-workflow.md` 第六章处理（拉取 diff → 用户选择）
- **Notion CLI 不可用** → 降级为 local，告知用户。详见 `notion-workflow.md` 第五章
- **Notion 未提供 URL / ID** → 直接提示用户补充，不自动猜测写入位置
- **Notion 给的是 database** → 仅在用户明确要求时在该 database 下创建页面；不自动推断标题字段名
- **Notion 页面需要大幅改写** → 默认覆盖正文内容；是否保留旧版本由用户自己决定
- **子 agent 失败** → 按 dispatch-strategies.md 3.4 处理
- **已有进行中计划** → 检查已有 TODO 和文档，询问继续还是新建
- **依赖未完成就派发** → 拒绝，提示完成前置任务
- **需求文档是链接** → WebFetch 获取，提取内容后进入 Step 1

## 限制

- 支持 `local` / `feishu` / `notion` 三种存储，但 `notion` 模式默认只覆盖文档内容，不保证复刻 UI 模板或项目结构
- 需求澄清最多 10 轮
- 子 agent 实施质量取决于 agent 对代码库的理解
- 不替代正式 PRD 流程或项目管理工具
- 伪代码仅描述逻辑，不保证可直接编译/运行
- 飞书文档富文本（表格、图片）在 CLI 读写中可能丢失格式
- Notion database 创建页面时可能需要用户显式提供标题字段信息；字段名未知时不应盲写
