# Outreach 插件

> 求职触达工具集 —— 根据 JD 与个人经历生成高回复率的打招呼语；自动投递简历工作流（搜索 → 筛选 → 招呼语 → 定制简历 → 投递），当前支持 BOSS直聘。

## 技能列表

| 技能 | 说明 | 触发方式 |
|------|------|---------|
| `gen-greeting` | 根据 JD 和个人经历材料生成打招呼语（主推版 + 超短版），内置证据分级匹配分析与自检清单，平台实践读本地 references，默认不联网 | "生成打招呼语" / "写打招呼" / "求职开场白" |
| `auto-apply` | 自动投递简历：按简历与求职偏好搜索岗位 → 智能筛选评分 → 生成打招呼语 → 按 JD 定制简历 → Patchright + 本机 Chrome 执行投递（频控 + 台账防重 + 验证码人工介入）。当前支持 BOSS直聘 | "自动投递简历" / "批量投简历" / "boss直聘投递" |

## 安装

```bash
# 通过 Marketplace（推荐）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon
/plugin install outreach@poseidon

# 或本地路径安装
/plugin install ./plugins/outreach
```

## gen-greeting 工作流

1. **收集输入**：JD（必需）+ 经历材料（简历或项目笔记；用户指定的经历文件优先）
2. **匹配分析**：JD 逐条拆解，按「商业交付 > 自研 > 学习」「职责同构 > 技术栈相似」「数字 > 形容词」选出唯一最匹配项
3. **写作标准**：直接读 `references/` 沉淀标准，默认不联网；仅用户明确要求刷新实践时才搜索并写回 reference
4. **生成**：主推版（100-130 字）+ 超短版（70-80 字），证据先行、术语为 HR 降维、匹配断言只放结尾
5. **自检输出**：9 条自检清单逐项核对，输出附调整逻辑说明

标准沉淀在 `skills/gen-greeting/references/`（打招呼语写作标准，auto-apply 复用）：

- `greeting-principles.md` — 写作标准（证据先行、结构公式、禁止清单、发送时机）
- `greeting-templates.md` — 模板库（主推/超短/自研钩子变体/展开版/跟进版，含真实案例改前改后对照）

## auto-apply 工作流

1. **准备登录**：扫码登录（cookie 约 7 天），配置 `~/.poseidon/outreach/config.json`
2. **搜索**：`search.py` 按「关键词 × 城市」抓取岗位（拦截页面数据接口：明文薪资、HR 姓名/在线、猎头标记、公司行业/规模、技能/福利标签、台账去重标记）；`filter.py` 预过滤出候选（黑名单/猎头/已投/岗位名门禁/去重）并把兼职计件薪资折算成时薪/日薪
3. **筛选**：Claude 只读 `candidates-<日期>.json`，按 `references/matching.md` 评分（技术栈 40 / 业务域 20 / 职责同构 20 / 质量 10 / 薪资 10），边界岗位（贴线/宽幅/可疑时薪）交用户决策
4. **物料**：`gen-greeting` 生成招呼语（超短版适配聊天框）+ `create-resume` 按 JD 定制简历（默认 top 3，只落盘，投递脚本不发送附件）
5. **投递**：`apply.py` 先 dry-run 验证链路，确认后 `--execute` 发送；浏览器前台/后台在首次配置 `headed` 时定死，投递前不再询问。日上限 50、随机间隔 8-20s、每 10 个长休息、验证码即停
6. **台账**：`delivered.json` 防重投（7 天），输出投递汇总与跟进建议

连接方式与选择器维护见 `skills/auto-apply/references/`（平台扩展索引：boss 已实现，猎聘/智联/51job/拉勾规划）。

## Roadmap

- [x] `auto-apply` — 搜索 → 筛选 → 招呼语 → 定制简历 → 投递（BOSS直聘，2026-10）
- [ ] 附件/图片简历自动发送（打招呼通过后，参考 get_jobs 图片简历实践）
- [ ] 平台扩展：猎聘 → 智联 → 51job（连接手册与脚本按 `platforms.md` 接入清单）
- [ ] `reply-tracker` — 跟踪已读/回复状态，定时跟进已读不回的会话
