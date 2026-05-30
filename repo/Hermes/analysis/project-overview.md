# 项目概览

## 基本信息
- **项目名称**：Hermes
- **一句话描述**：基于 OpenClaw + ClawHub 技能生态的加密货币长线趋势分析系统，通过「主脑编排 + 社区技能组合 + 自定义知识库」形成决策流程固定、输出格式一致、有 Source of Truth 支撑的 AI 分析工具。
- **在线链接**：<待补充>
- **项目类型**：AI Agent 技能系统 / 声明式编排工具

## 业务领域
- **行业/场景**：加密货币 / AI Agent 自动化 / 交易决策辅助
- **目标用户**：加密货币长线投资者，需 AI 辅助但不依赖 AI 决策的交易者
- **核心功能**：
  1. 加密货币多维度趋势分析（技术面 + 结构形态 + 基本面 + 消息面）
  2. 长线/短线双模式分析路由，适配不同持仓周期
  3. 多币种横向对比选币评分与排名
  4. 基于分析报告的交易策略制定（入场/止损/止盈/仓位计算）
  5. 交易记录与持仓跟踪（止盈止损监控 + 持仓状态查询）

## 架构概览
- **架构模式**：纯路由 + 编排器 + 子 Agent 双层架构（SKILL.md 路由 → analyzer-orchestrator 编排 → 5 专业子 agent 并行执行）
- **工程结构**：
  - `skills/trade/` — 主技能目录（SKILL.md 路由器 + agents/ 指令 + references/ 知识库 + scripts/ 脚本）
  - `docs/` — 架构文档与产品设计文档
  - `.hermes/` — 本地中间数据（分析报告、交易记录、扫描结果，不提交 Git）
- **模块划分**：
  - SKILL.md 路由器 — 意图解析（币种 + 长短线模式）+ 路由派发
  - analyzer-orchestrator — 单币种分析编排（长线/短线路由 + 铁律对照 + 量化评分 + 报告输出）
  - data-fetcher — 行情数据获取（OKX API 对接）
  - technical-analyst — 多周期技术指标分析（EMA/ADX/RSI/MACD/布林带/ATR）
  - structure-analyst — ICT/SMC 结构分析 + Wyckoff 阶段判断
  - fundamental-analyst — 基本面分析（团队/代币经济/解锁风险/链上数据）
  - news-analyst — 消息面搜索（新闻/链上动态/宏观事件）
  - coin-picker — 多币种横向对比选币（分批扫描 + 评分排名）
  - trading-strategist — 交易策略制定与执行（报告驱动 → Source of Truth 对照 → 用户确认 → OKX API 执行）
  - trade-tracker — 交易记录与持仓跟踪（.hermes/trades/ 读写 + 止盈止损监控）

## 技术亮点
- 纯路由 + 编排器双层解耦架构：SKILL.md 仅 ~100 行做意图解析与派发，所有分析逻辑下沉到子 agent 指令文件，新增币种或分析维度只需加一行路由
- 子 Agent 并行策略：data-fetcher 必须先执行获取数据，之后 technical/structural/fundamental/news 四个 agent 并行运行，在编排器中汇总与冲突检测
- 三级渐进式上下文加载：L1 frontmatter（~100 token）→ L2 SKILL.md body（<5000 token）→ L3 agents/references/scripts 按需加载，Token 预算精准控制
- 交易安全四层防护：权限卡控 → 频率限制 → 金额上限 → 人工确认，API Key 仅读权限 + 物理隔离
- 确定性与推理分离：格式化、归档、批量队列等确定性计算用 Python 脚本；市场分析、策略判断等推理保留在 agent 指令中
- 8 个数据流覆盖全场景：标准分析 / 短线分析 / 批量扫描 / 定时调度 / 多币种选币 / 报告持久化 / 交易策略 / 持仓跟踪

## 简历可用素材
以下信息可直接用于简历项目描述：

- **项目角色**：独立开发（12 次提交，唯一贡献者）
- **关键词**：AI Agent 编排、OpenClaw 技能系统、声明式指令工程、Python 脚本、OKX API 集成、加密资产分析、多 Agent 并行架构
- **是否有在线 Demo**：<待补充>
