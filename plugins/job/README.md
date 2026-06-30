# Job 插件

> 求职机会分析插件，面向城市定向求职场景，沉淀企业发现、岗位筛选、公开风评整理和报告输出所需的 skill、事实源和模板资产。

## 技能列表

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `job-opportunity-analyzer` | 半自动求职分析工作流：围绕目标城市、岗位关键词和候选公司池，整理公开来源信息并输出结构化分析报告、数据 schema 和来源清单 | 用户要求分析某城市/岗位机会、筛选公司池、整理求职事实源 |

## 首期范围

- `job-opportunity-analyzer` 主 skill 的目录骨架、占位入口和资源分层
- 面向公开信息的半自动分析链路设计：企业发现、岗位机会筛选、公司风评整理、报告输出
- 报告模板、样例资源、schema 和来源清单的放置规则

## 首期不做

- 需要登录的网站接入、账号体系和反爬绕过
- 定时刷新、持续监控和自动化调度
- 简历改写、自动投递、消息通知等后续闭环能力

## 范围外提醒

- README 中提到的扩展方向只是后续演进预留，不代表当前插件已经支持。
- 首期实现仍然只围绕 `job-opportunity-analyzer` 这一个主 skill 展开，不新增多 skill 骨架，不提前引入复杂编排。
- 自动投递、实时抓取、外部账号集成、通知提醒等能力明确不进入首期，即使后续文档讨论相关方向，也只能作为未来路线，不得混入当前交付。

## 安装

```bash
# 先生成平台插件包
python scripts/install.py --platform claude --scope repo --plugin job --yes

# 通过 Marketplace（推荐）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon
/plugin install job@poseidon

# 或本地路径安装
/plugin install ./plugins/job
```

## 目录结构

```text
job/
├── README.md
├── assets/                                      # 插件级共享静态资源：通用模板、示例素材
│   └── README.md
├── references/                                  # 插件级共享参考资料：跨 skill 通用方法论
│   └── README.md
├── scripts/                                     # 插件级共享脚本：确定性校验与构建辅助
│   └── README.md
└── skills/
    └── job-opportunity-analyzer/
        ├── SKILL.md                             # 主 skill 占位入口，完整流程后续补充
        ├── assets/                              # skill 私有模板、schema、样例数据
        │   └── README.md
        ├── references/                          # skill 私有引用资料：企业发现、来源清单、报告模板
        │   └── README.md
        └── scripts/                             # skill 私有确定性脚本：schema 校验、样例检查
            └── README.md
```

## 资源分层规则

- 优先把资料放在 skill 私有目录：只服务 `job-opportunity-analyzer` 的 schema、报告模板、来源方法论，直接放在该 skill 的 `references/`、`assets/`、`scripts/`。
- 只有明确跨 skill 复用时，才提升到插件根目录：例如未来多个求职 skill 共享的城市来源规范、报告样式模板或通用校验脚本。
- Markdown 用于知识沉淀和操作指南；脚本只负责确定性处理，例如 schema 校验、样例文件检查和模板拼装辅助。

## 维护说明

- 首期维护是轻维护模式，不承诺实时刷新，也不引入定时调度或通知链路。
- 默认先阅读 `plugins/job/skills/job-opportunity-analyzer/references/maintenance.md`，按其中的来源频率、失效替换和人工复核规则更新资料。
- 每次改动结构化样例后，至少运行一次校验脚本：

```bash
python3 plugins/job/skills/job-opportunity-analyzer/scripts/validate-company-pool.py
```

- 如果只是更新方法论或来源说明，也要做手工自检，确认覆盖了新增、更新、下线、复核四类动作。
- 遇到链接失效、公司已倒闭、岗位长期陈旧或业务明显偏离目标岗位时，不要直接删除记录；先按 `maintenance.md` 标记降级、替换来源或触发人工复核。

## 计划中的首期文件

- `plugins/job/README.md`
- `plugins/job/assets/README.md`
- `plugins/job/references/README.md`
- `plugins/job/scripts/README.md`
- `plugins/job/skills/job-opportunity-analyzer/SKILL.md`
- `plugins/job/skills/job-opportunity-analyzer/assets/README.md`
- `plugins/job/skills/job-opportunity-analyzer/references/README.md`
- `plugins/job/skills/job-opportunity-analyzer/scripts/README.md`

## 后续扩展路线

以下方向仅作为演进预留，便于后续评估，不属于首期交付范围：

1. 多城市、多岗位族群扩展
   当前样例聚焦单城市、单岗位方向。后续可以扩展到更多城市、更多岗位族群，以及跨城市对比样例，但首期不新增多城市数据骨架，也不扩大样例维护面。
2. 多 skill 拆分
   如果后续 `job-opportunity-analyzer` 证明边界稳定，可以再拆出独立 skill，例如 `company-discovery`、`resume-targeting`、`application-tracker`。首期不预建这些目录，不提前引入多 skill 协作复杂度。
3. 更严格的校验与报告辅助
   后续可以增加更严格的结构校验、报告拼装辅助脚本、样例一致性检查等确定性工具。首期只保留必要校验，不建设完整生成流水线。
4. 更丰富的公开来源维护
   后续可以扩展更多地方名单、行业榜单、高校就业网和招聘平台来源目录，并沉淀按城市或岗位细分的维护规则。首期先以可维护的方法论和样例闭环为主，不追求大而全的来源覆盖。

## 首期边界总结

- 当前交付只承诺一个主 skill、有限样例资产、公开来源方法论和确定性校验脚本。
- 后续可扩展方向不能被描述成“已支持”或“默认启用”能力。
- 如果未来要进入简历定制、投递跟踪、通知闭环或实时刷新，应作为新阶段需求单独规划，而不是继续塞入首期范围。
