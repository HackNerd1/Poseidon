# 技术栈分析结果

## 语言
- Markdown（25 文件，占比最高 — SKILL.md、agents、references 等声明式指令文件）
- Python（5 文件 — 确定性计算脚本）
- JSON（3 文件 — 配置文件）

## 框架与运行时
| 名称 | 类别 | 判断依据 |
|------|------|---------|
| OpenClaw | AI Agent 运行时平台 | README + 架构文档明确说明 |
| Claude Code | AI Agent 平台 | 架构文档中提及同态兼容 |
| Agent Skills 开放标准 | 技能规范 | SKILL.md 遵循 agentskills.io 标准 |

## 构建与工具链
| 名称 | 用途 | 判断依据 |
|------|------|---------|
| OpenClaw Skill System | 技能加载与管理 | agents/、references/、scripts/ 三级渐进式加载架构 |
| Bash | 脚本执行 | verify_deps.sh 依赖验证脚本 |
| Python 3 | 确定性计算 | report_template.py、batch_scan.py、coin_screener.py、history_archive.py、trade_recorder.py |

## 状态管理与数据层
| 名称 | 用途 | 判断依据 |
|------|------|---------|
| 本地 JSON 文件系统 | 中间数据持久化 | .hermes/ 目录结构（reports/、trades/、comparisons/、history/） |
| ChromaDB | 向量检索（依赖技能） | OpenMobius 技能使用 ChromaDB 存储 964 张知识卡片 |

## 测试
- 无自动化测试框架（项目为声明式 AI Agent 技能编排系统，验证依赖手动执行 verify_deps.sh）

## 基础设施
| 名称 | 用途 | 判断依据 |
|------|------|---------|
| Git | 版本控制 | .git 目录 + 12 次提交历史 |
| OKX API | 加密货币行情数据源 | README + 架构文档中描述的数据层依赖 |
| Dune/Nansen | 链上数据分析（规划） | 架构文档 v1.0 版本规划 |

## 外部技能依赖（核心生态）
| 技能 | 来源 | 角色 |
|------|------|------|
| okx/agent-skills | OKX 官方 | 数据层 — 82 工具 CEX 行情/链上数据 |
| technical-indicator-pro | ClawHub | 指标层 — 50+ 指标多周期计算 |
| market-structure | ClawHub | 形态层 — SMC/ICT 方法论分析 |
| RootData | ClawHub | 基本面 — 项目/团队/融资/代币数据 |
| openmobius-skill | GitHub | 知识层 — 964 卡片向量检索 + K 线标注 |

## 技术栈汇总（供简历使用）

按使用程度分两层：

**核心：** AI Agent 技能编排、OpenClaw 平台、声明式指令工程（Markdown）、Python 脚本
**辅助：** OKX API 集成、JSON 数据持久化、Git 版本控制
