---
name: plan
description: '从需求到实施的渐进式计划工作流。当用户提供需求描述/文档链接要求制定实施计划、澄清需求、拆分任务时触发。适用场景：需求澄清与评分、需求文档生成、总体计划制定、详细任务拆分、分批派发子 agent 实施。支持本地 Markdown、飞书 CLI、Notion CLI 三种文档存储方式。触发短语："帮我做计划"、"plan this"、"分析需求"、"拆分任务"、"制定实施方案"、"clarify requirements"、"create implementation plan"。'
---

# Plan Skill — 从需求到实施的渐进式计划工作流

## 概述

你将帮助用户将模糊需求逐步转化为可执行的实施计划。核心原则：**先澄清、再计划、后派发**。流程覆盖：输入验证 → 需求探讨 → 需求文档 → 总体计划 → 详细计划 → 派发实施 → 循环迭代。

你充当 Claude-Native Loop Controller：读取参考模板、评估需求清晰度、调度子 agent 执行任务、通过 TODO 跟踪进度。

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
- 六维评估框架与 100 分制评分标准（第二章）
- 模糊词翻译表（第三章）
- 提问模板（第四章）
- 快速评分卡（第六章）

#### 1.2 首次评估

按六维框架（目标清晰度 20 / 范围边界 15 / 功能明确性 30 / 技术约束 15 / 业务上下文 20）对需求首次评分。给出总分和低分维度。

#### 1.3 联网补充（可选）

需求领域不常见时搜索网络获取背景知识，交叉比对发现遗漏点。

#### 1.4 多轮提问

- 每轮 **2-3 个问题**，优先解决评分最低的维度
- 尽量给出选项（A/B/C），量化模糊词，每轮结束复述理解
- **上限 10 轮**。超过仍未达 90 分 → 告知用户，建议先进入计划

#### 1.5 评分更新与总结

每轮更新评分（如"45 → 65，+20"）。≥90 分后，按指南第七章模板生成澄清记录：

**输出**（local）：`docs/requirements/<feature-slug>-clarification.md`
**输出**（feishu）：先写入 `.Poseidon/feishu/<slug>-clarification.md`，再按 `feishu-workflow.md` 三.1 节推送至飞书。
**输出**（notion）：先写入 `.Poseidon/notion/<slug>-clarification.md`，再按 `notion-workflow.md` 第四章推送至 Notion。

告知用户评分和记录路径，确认后进入 Step 2。

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

生成后按模板质量检查清单自检。

**输出**（local）：`docs/requirements/<feature-slug>.md`
**输出**（feishu）：先写入 `.Poseidon/feishu/<slug>-requirement.md`，再推送飞书，更新 `doc-map.json`。
**输出**（notion）：先写入 `.Poseidon/notion/<slug>-requirement.md`，再推送 Notion，更新 `doc-map.json`。

确认后进入 Step 3。

### Step 3：生成总体计划

> **L3 加载**：`references/overall-plan-template.md`、`references/code-execution-standards.md`（Plan Agent Prompt 模板）

#### 3.1 评估是否需要总体计划

改动很小（单文件修改、配置变更、Bug 修复、预估 ≤3 个任务）→ 跳过，告知用户后直接进入 Step 4。

否则进入 3.2。

#### 3.2 派发 Plan Agent 生成总体计划

Read `references/overall-plan-template.md` 了解文档结构。
Read `references/code-execution-standards.md` 第二章获取 Plan Agent Prompt 模板。

按模板构造 prompt，包含：需求文档路径、澄清记录路径、架构约束、阶段划分原则。

使用 **Agent tool** 派发 `Plan` 类型子 agent：

```
Agent tool:
  description: "Generate overall plan for <feature-name>"
  prompt: <按 code-execution-standards.md 第二章模板构造>
  subagent_type: "Plan"
```

#### 3.3 验证与 TODO 创建

子 agent 完成后，按 `code-execution-standards.md` 5.1 节验收：
- [ ] 计划文档已写入指定路径
- [ ] 文档结构符合 overall-plan-template.md
- [ ] 阶段划分符合垂直切片原则
- [ ] 依赖关系明确，无循环依赖

通过后为每个阶段的宏观任务创建 TODO（TaskCreate）。

**输出**（local）：`docs/requirements/<feature-slug>-overall-plan.md`
**输出**（feishu）：先写入 `.Poseidon/feishu/<slug>-overall-plan.md`，再推送飞书。
**输出**（notion）：先写入 `.Poseidon/notion/<slug>-overall-plan.md`，再推送 Notion。

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

#### 4.2 派发 Plan Agent 生成详细计划

Read `references/plan-template.md` 了解文档结构。
Read `references/code-execution-standards.md` 第二章获取 Plan Agent Prompt 模板。

按模板构造 prompt，包含：需求文档路径、总体计划路径（如有）、澄清记录路径、架构约束、任务拆分原则（垂直切片、粒度 S/M、独立可测、依赖清晰）。

使用 **Agent tool** 派发 `Plan` 类型子 agent：

```
Agent tool:
  description: "Generate detailed plan for <feature-name> Phase <N>"
  prompt: <按 code-execution-standards.md 第二章模板构造>
  subagent_type: "Plan"
```

如果多个阶段可并行规划，可同时派发多个 Plan agent（如 Phase 2 和 Phase 3 同时规划）。

#### 4.3 验证与 TODO 创建

子 agent 完成后，按 `code-execution-standards.md` 5.1 节验收：
- [ ] 任务拆分粒度合理（S/M 规模，3-7 个/阶段）
- [ ] 每个任务有明确的验收标准和验证方式
- [ ] 依赖关系图无循环，并行任务已标注
- [ ] 架构约束已纳入考量

通过后为每个叶子任务创建 TODO（TaskCreate）。

**输出**（local）：`docs/requirements/<feature-slug>-detailed-plan-p<n>.md`
**输出**（feishu）：先写入 `.Poseidon/feishu/<slug>-detailed-plan-p<n>.md`，再推送飞书。
**输出**（notion）：先写入 `.Poseidon/notion/<slug>-detailed-plan-p<n>.md`，再推送 Notion。

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

派发时使用 **Agent tool**（`general-purpose` 类型），按 `code-execution-standards.md` 第三章 Prompt 模板构造，**必须注入以下开发规范**：
1. 关键代码必须添加注释（公共函数、复杂逻辑、非显而易见的决策）
2. 核心逻辑必须添加测试用例（Happy Path + 边界值 + 异常路径）
3. 遵循项目架构约束文档（目录结构、命名规范、错误处理模式）
4. 先搜索项目中类似实现，保持风格一致；不确定时搜索网络最佳实践

子 agent 完成后按 `dispatch-strategies.md` 3.3 节逐项验证（验收标准 + 注释 + 测试 + 风格一致性），不通过则要求补充。

### Step 6：更新与循环

#### 6.1 任务完成后更新

每个子 agent 完成后，按 `code-execution-standards.md` 5.2 节验收：
- 验收标准逐条达成 → 标记 `[x]`
- 注释/测试/风格不通过 → 要求补充后重新提交

通过后：
1. 更新详细计划文档：标记完成项 `[x]`
2. 更新总体计划文档：阶段内全部完成则标记阶段完成
3. 更新 TODO：TaskUpdate 标记 `completed`

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
├── 📝 需求澄清：<score>/100 分 | <path>
├── 📄 需求文档：<path>
├── 🗺️ 总体计划：<N> 阶段 <M> 任务 | <path>
├── 📐 详细计划：Phase <current> | <path>
├── ✅ 已完成：<done>/<total> 任务
├── 🔜 下一阶段：<next phase or "无">
└── 📚 架构约束来源：<path or "通用最佳实践">
```

## 关键规则

1. **先澄清再计划**：≥90 分或 10 轮上限后进入计划阶段
2. **每轮 2-3 个问题**：给选项减少输入；量化模糊词
3. **渐进式加载**：每步开始时显式 Read 对应 reference，不过早加载
4. **计划文档可追溯**：每个文档关联上一步文档，形成完整链
5. **TODO 同步更新**：TaskCreate/TaskUpdate 与文档同步
6. **架构约束优先**：未找到约束文档时主动询问
7. **垂直切片原则**：按功能切片不按技术层切分
8. **子 agent 不自动派发**：必须用户确认
9. **进度持久化**：所有文档和 TODO 写入文件系统，支持中断恢复
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
