# Plan Skill 第一性原理审查

> 日期：2026-07-10
> 目标：记录 `plugins/dev-tools/skills/plan` 当前存在的关键不足、风险和后续优化方向，作为后续修复 backlog

## 结论摘要

当前 `plan` skill 的核心问题不是“模板不够完整”，而是“方法论、工具能力、执行闭环”三者没有真正对齐。

从第一性原理看，一个 planning skill 的最小成立条件应是：

1. 能把模糊需求转成足够支撑决策的结构化信息
2. 能产出可执行、可验证、可追踪的计划
3. 能与当前真实可用的工具和环境闭环
4. 产出的流程成本低于它带来的返工节省

当前版本在第 3 点和第 4 点上问题最明显。

## 问题清单

### P0: 执行闭环不成立

- 现状：
  `SKILL.md` 反复依赖 `Agent tool`、`Plan` 子 agent、`TaskCreate`、`TaskUpdate` 等能力来完成总体计划、详细计划、实施派发和进度跟踪。
- 问题：
  这些能力在 skill 文本中没有和当前可用工具面建立明确映射，导致流程是“概念闭环”，不是“系统闭环”。
- 风险：
  用户以为 skill 可直接运行完整 workflow，但实际执行时会在派发或 TODO 同步阶段中断。
- 相关位置：
  - `plugins/dev-tools/skills/plan/SKILL.md:116`
  - `plugins/dev-tools/skills/plan/SKILL.md:129`
  - `plugins/dev-tools/skills/plan/SKILL.md:193`
  - `plugins/dev-tools/skills/plan/SKILL.md:206`
  - `plugins/dev-tools/skills/plan/references/code-execution-standards.md:12`
- 修复建议：
  - 明确每个抽象能力对应的真实工具调用方式
  - 若当前环境没有 TODO 系统，就删除 `TaskCreate/TaskUpdate` 依赖，退化为纯文档状态跟踪
  - 若没有独立 `Plan` 子 agent 类型，就统一收敛为当前真实可用的子 agent 类型

### P0: 远端文档工作流与当前工具生态脱节

- 现状：
  飞书 workflow 使用 `feishu doc create/update/export`、`feishu auth`，Notion workflow 使用 `ntn` 配合 shell 重定向、命令替换和内联 Python。
- 问题：
  这些命令描述更像“示意命令”，不是当前仓库内经过验证的稳定协议。
- 风险：
  `feishu` 模式和 `notion` 模式都可能在真实执行时失败，最终只能手工兜底。
- 相关位置：
  - `plugins/dev-tools/skills/plan/SKILL.md:37`
  - `plugins/dev-tools/skills/plan/references/feishu-workflow.md:73`
  - `plugins/dev-tools/skills/plan/references/feishu-workflow.md:196`
  - `plugins/dev-tools/skills/plan/references/notion-workflow.md:66`
  - `plugins/dev-tools/skills/plan/references/notion-workflow.md:78`
- 修复建议：
  - 飞书部分改成基于当前真实可用的 `lark-cli` 协议重写
  - Notion 部分补齐“受限环境下如何执行”的明确策略
  - 所有命令示例分成“已验证命令”和“伪代码示意”两类，避免误导

### P1: 把“需求清晰”误建模成“评分达到 90 分”

- 现状：
  skill 用六维评分和 `>=90` 门槛决定是否进入计划阶段。
- 问题：
  这会驱动模型去追求“高分需求”，而不是优先消除真正阻塞计划和实施的关键不确定性。
- 风险：
  会出现“分数很高但仍缺关键约束”的假清晰；也会出现“分数不高但已足够实施最小切片”的过度澄清。
- 相关位置：
  - `plugins/dev-tools/skills/plan/SKILL.md:59`
  - `plugins/dev-tools/skills/plan/SKILL.md:69`
  - `plugins/dev-tools/skills/plan/SKILL.md:73`
  - `plugins/dev-tools/skills/plan/references/requirement-clarification-guide.md:72`
- 修复建议：
  - 用“阻塞未知数清单”替代单一总分门槛
  - 进入计划的条件改为：
    - 关键决策所需信息已齐备
    - 剩余未知数不会改变当前阶段方案
    - 可先做最小验证切片

### P1: 默认流程过重，交互成本偏高

- 现状：
  默认路径接近 `澄清 -> 需求文档 -> 总体计划 -> 详细计划 -> 派发确认`，且多个阶段要求显式确认。
- 问题：
  对中小需求而言，计划过程本身可能已经重于需求本身。
- 风险：
  用户为了“做个小计划”被拉入文档工程，削弱 skill 的实用性。
- 相关位置：
  - `plugins/dev-tools/skills/plan/SKILL.md:45`
  - `plugins/dev-tools/skills/plan/SKILL.md:77`
  - `plugins/dev-tools/skills/plan/SKILL.md:105`
  - `plugins/dev-tools/skills/plan/SKILL.md:252`
- 修复建议：
  - 增加 fast path
  - 对小需求直接输出 micro-plan：
    - 目标
    - 关键约束
    - 3-5 个执行步骤
    - 验收方式
  - 只在中大型、多阶段、多人协作需求时进入完整 workflow

### P1: planning 职责和 coding/execution policy 耦合过重

- 现状：
  `code-execution-standards.md` 同时承载计划生成模板、代码注释规范、测试规范、风格约束和验收逻辑。
- 问题：
  `plan` skill 的边界被拉宽，职责混杂。
- 风险：
  一旦执行规范变化，就会连带影响 planning skill；而 planning skill 在非代码场景的泛化能力也会下降。
- 相关位置：
  - `plugins/dev-tools/skills/plan/references/code-execution-standards.md:109`
  - `plugins/dev-tools/skills/plan/references/code-execution-standards.md:165`
  - `plugins/dev-tools/skills/plan/references/code-execution-standards.md:176`
- 修复建议：
  - 把计划模板与执行规范拆开
  - `plan` skill 只负责：
    - 澄清
    - 分阶段
    - 任务拆分
    - 依赖与验收设计
  - 代码注释、测试、风格要求改为引用独立 execution skill 或 repo policy

### P1: 架构约束发现机制过于表层

- 现状：
  当前主要从 `docs/architecture.md`、`CLAUDE.md`、`README.md` 提取架构约束。
- 问题：
  真实约束往往分散在 lint/test config、scripts、CI、目录模式和现有实现中。
- 风险：
  计划文档看似规范，实际实施时大量返工。
- 相关位置：
  - `plugins/dev-tools/skills/plan/SKILL.md:137`
  - `plugins/dev-tools/skills/plan/references/code-execution-standards.md:196`
- 修复建议：
  - 增加约束探测顺序：
    - 显式架构文档
    - package manager / build / test scripts
    - lint / formatter / type checker 配置
    - 现有同类模块实现
    - CI 工作流
  - 将“架构约束来源”作为计划文档中的必填元数据

### P2: 文档事实源模型不统一

- 现状：
  `local` 模式写 `docs/requirements/`，远端模式写 `.Poseidon/feishu/` 或 `.Poseidon/notion/` 本地副本，再同步远端。
- 问题：
  没有统一 canonical artifact 模型，也没有真正严谨的版本冲突策略。
- 风险：
  长期维护时会不清楚：
  - 哪份是事实源
  - 哪份是同步副本
  - 哪份允许人工修改
- 相关位置：
  - `plugins/dev-tools/skills/plan/SKILL.md:18`
  - `plugins/dev-tools/skills/plan/references/feishu-workflow.md:143`
  - `plugins/dev-tools/skills/plan/references/notion-workflow.md:175`
- 修复建议：
  - 统一为“单一本地 canonical markdown”
  - `docs/requirements/` 或 `.Poseidon/plan-artifacts/` 二选一作为唯一事实源
  - 飞书/Notion 都视为 projection，不再并列为另一份“本地事实源”

### P2: 缺少计划质量反馈回路

- 现状：
  现有验收主要检查文档结构和规则符合性。
- 问题：
  没有衡量计划是否真的降低返工、提升并行度、减少阻塞。
- 风险：
  skill 会持续朝“模板更完整”优化，而不是朝“交付更有效”优化。
- 相关位置：
  - `plugins/dev-tools/skills/plan/references/code-execution-standards.md:221`
- 修复建议：
  - 为后续迭代增加 plan effectiveness 指标，例如：
    - 实际任务数 vs 预估任务数偏差
    - 重新规划次数
    - 并行任务冲突次数
    - 验收失败回退次数
    - 因需求不清导致的返工次数

## 推荐整改顺序

### 第一批：先修闭环

1. 去掉或替换当前不可落地的 `TaskCreate/TaskUpdate`
2. 明确子 agent 类型与真实工具映射
3. 重写 Feishu / Notion workflow 为当前真实可执行版本

### 第二批：再修方法论

1. 用“阻塞未知数”替代“90 分门槛”
2. 加入 small-task fast path
3. 收缩 `plan` skill 的职责边界

### 第三批：最后修可维护性

1. 统一文档事实源模型
2. 增强架构约束发现机制
3. 增加计划效果度量与复盘机制

## 预期目标

后续修复完成后，`plan` skill 应收敛为：

- 对小需求足够轻
- 对大需求足够稳
- 对当前工具面足够真
- 对后续实施足够有约束力
- 对未来维护者足够可理解

