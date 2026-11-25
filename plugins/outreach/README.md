# outreach

**求职触达插件 —— 按 JD 生成高回复率的打招呼语，并把“搜岗 → 筛选 → 招呼语 → 定制简历 → 投递”串成可核实的自动投递流程。**

当前支持 BOSS直聘（Patchright 驱动本机 Chrome，扫码登录、频控、验证码人工介入）与 remotecn feeds 直连搜索（远程岗聚合，只查不落盘）。仅限本人求职使用，默认人工确认制。

## 技能一览

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `gen-greeting` | 根据 JD 和个人经历生成打招呼语（主推版 + 超短版），内置证据先行写作标准与最匹配项分级排序，平台实践读本地 references，默认不联网 | “生成打招呼语”“写打招呼”“求职开场白” |
| `auto-apply` | 自动投递：按简历与偏好搜索岗位 → 筛选评分 → 生成招呼语 → 按 JD 定制简历 → 执行投递，含频控、台账防重与验证码人工介入；另提供 remotecn 远程岗直连搜索 | “自动投递简历”“批量投简历”“boss直聘投递”“搜远程岗位” |

## 安装

前置条件：Python 3 与 `git`；使用 Claude Code 或 Codex 插件流程时需已安装对应 CLI。

```bash
git clone https://github.com/HackNerd1/Poseidon.git
cd Poseidon
python3 scripts/install.py --platform claude --scope user --plugin outreach
```

把 `--platform` 换成 `codex` 或 `cursor` 可装到其他平台；`--scope repo` 安装到当前项目而非用户级目录。

## 使用

```text
/gen-greeting
/auto-apply
```

`gen-greeting` 只需要 JD 与经历材料，可以单独使用；`auto-apply` 默认先展示参数与筛选结果，确认后才执行投递。

## gen-greeting 工作流

1. **收集输入**：JD（必需）+ 经历材料（简历或项目笔记，用户指定的经历文件优先）
2. **匹配分析**：JD 逐条拆解，按“商业交付 > 自研 > 学习”“职责同构 > 技术栈相似”“数字 > 形容词”选出唯一最匹配项
3. **写作标准**：直接读 `references/` 沉淀的标准，默认不联网；仅用户明确要求刷新实践时才搜索并写回 reference
4. **生成**：主推版（100–130 字）+ 超短版（70–80 字），证据先行、术语为 HR 降维、匹配断言只放结尾
5. **自检输出**：9 条自检清单逐项核对，输出附调整逻辑说明

标准沉淀在 `skills/gen-greeting/references/`，`auto-apply` 复用同一套：

- `greeting-principles.md` — 写作标准（证据先行、结构公式、禁止清单、发送时机）
- `greeting-templates.md` — 模板库（主推/超短/自研钩子变体/展开版/跟进版，含案例改前改后对照）

## auto-apply 工作流

1. **准备登录**：扫码登录（cookie 约 7 天）。每次启动用 `filter.py --show-config` 确认参数（含折算公式与 `hoursPerDay`），并询问今日目标条数
2. **搜索**：按目标循环 `search.py` → `filter.py --table --merge-rounds`，同日快照按岗位 id 去重；新增候选耗尽或可投达到目标即停，不超额
3. **筛选**：评分读 `--table`，不读候选 JSON；勾选前用 `detail.py --links` 批量拉详情，硬条件由脚本打标
4. **物料**：`gen-greeting` 生成招呼语 + `create-resume` 按 JD 定制简历（只落盘，投递脚本不发送附件）
5. **投递**：`apply.py` 先 dry-run，确认后加 `--execute`；同日 `search+detail` 超过 6 次后脚本强制冷却，日上限默认 50，出现验证码即停
6. **台账**：execute 后必跑 `--verify`；`delivered.json` 防重投（7 天）并记录 `replyStatus`

remotecn 渠道与 BOSS 工作流相互独立：直连公开 API 搜索远程岗，只查不落盘，投递环节产出招呼语/自荐信草稿，由用户人工发送。

连接方式与选择器维护见 `skills/auto-apply/references/`（平台扩展索引：BOSS 已实现，猎聘/智联/51job/拉勾规划中）。

## 运行环境

| 依赖 | 说明 |
|------|------|
| Python 3.10+ | auto-apply 脚本环境 |
| `patchright` | 浏览器驱动，必须使用 patchright，不用原生 Playwright（会被识别导致空白页） |
| 本机 Google Chrome | 使用 `channel=chrome`，不使用捆绑 Chromium |
| 平台 CLI | Claude Code / Codex / Cursor，通过 `scripts/install.py --platform` 选择 |

依赖清单位于 `plugins/outreach/skills/auto-apply/scripts/requirements.txt`；首次使用的 venv 创建与扫码登录步骤由 `auto-apply` 技能引导完成。

## 路线

- [x] `auto-apply` — 搜索 → 筛选 → 招呼语 → 定制简历 → 投递（BOSS直聘，2026-10）
- [x] `auto-apply` — remotecn feeds 直连搜索（远程岗）
- [ ] 附件/图片简历自动发送（打招呼通过后）
- [ ] 平台扩展：猎聘 → 智联 → 51job（按 `platforms.md` 接入清单）
- [ ] `reply-tracker` — 跟踪已读/回复状态，定时跟进已读不回会话

## 许可证

[MIT License](../../LICENSE)，Copyright (c) 2026 HackNerd1。
