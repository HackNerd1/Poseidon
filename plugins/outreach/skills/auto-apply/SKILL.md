---
name: auto-apply
description: 自动投递简历工作流：按用户简历与求职偏好，在招聘平台搜索岗位 → 智能筛选 → 生成打招呼语 → 按JD定制简历 → 执行投递。当前支持 BOSS直聘（Patchright 驱动本机 Chrome，扫码登录，频控+验证码人工介入）。当用户要求"自动投递简历"、"批量投简历"、"自动打招呼"、"boss直聘投递"、"筛选岗位并投递"、"今天投几条"时触发。仅限用户本人求职使用，默认人工确认制。
---

# 自动投递简历工作流（auto-apply）

## 概述

编排器角色：脚本负责浏览器 I/O 与可规则化的筛选，你负责判断（评分、打招呼语、简历定制、是否再开一轮搜索）。串联 `gen-greeting` 与 `create-resume`，完成「确认参数 → 搜索至目标 → 详情复核 → 物料 → 投递 → 核实台账」。

**四条红线：**
1. **默认人工确认**：启动参数、筛选结果、最终投递都必须经用户确认（`autoConfirm=true` 只跳过勾选，仍要展示清单）。不得代用户确认配置，不得代填 `hoursPerDay`
2. **频控保守**：日上限默认 50。同日 `search+detail` 会话超过 6 次后，`--execute` / `--verify` 由脚本强制冷却 ≥180s（`COOLDOWN_REQUIRED` 是在等，不是卡死；没有绕过开关）
3. **验证码即停**：出现安全验证/滑块就停批次、截图、转人工，绝不自动过验
4. **台账防重**：同岗位 7 天内不重投；不虚报简历；不超额投过今日目标 N

## 数据目录

所有状态存 `~/.poseidon/outreach/`（`OUTREACH_DATA_DIR` 可覆盖）：

```
~/.poseidon/outreach/
├── config.json
└── boss/
    ├── profile/                 # 登录态
    ├── jobs-<日期>*.json        # 搜索快照；同日多轮靠这些文件按 id 去重
    ├── candidates-<日期>.json   # 候选+边界。评分读 --table，不要把这份读进对话
    ├── screen-<日期>.json       # 淘汰审计，调阈值时才读
    ├── detail-<id>.json         # JD / 条款 / jdFlags
    ├── sessions.json            # 同日浏览器会话计数（频控预算）
    ├── plan-<批次>.json
    ├── plan-*.result-*.json / plan-*.verify-*.json
    ├── delivered.json           # 台账；每条有 replyStatus（unread/read/replied/no_reply）
    ├── diag/                    # no_input 时的 {tag, pages[]}
    ├── resumes/
    └── screenshots/
```

同日重跑：`jobs/candidates/screen` 同名文件轮转为 `-HHMM`，不覆盖。可删 `*-test*`、`*smoke*`、已结束岗位的 `detail-*.json`、过期快照。不要动 `config.json`、`delivered.json`、`profile/`。

## 首次使用

```bash
VENV=~/.poseidon/outreach/.venv
python3 -m venv $VENV
$VENV/bin/pip install -r scripts/requirements.txt
$VENV/bin/python scripts/boss/login.py    # 弹窗扫码，10 分钟超时
```

配置不存在时先收集再写入：城市代码（`references/boss-zhipin.md`）、岗位词关键词（「前端/Electron」，不要「远程办公」）、`headed`、日上限、黑名单。兼职（`jobType=1903`）还必须有用户亲口给的 `hoursPerDay` 和 `salaryFloorDay`。`search.py --config` 缺这些字段会 `CONFIG_MISSING` 拒绝，不要用默认值绕过。`skipInactiveDays` 是死配置，脚本打印 `IGNORED`。

## 工作流

复制这份清单，做完一项勾一项：

```
投递进度:
- [ ] login.py --check 已确认登录态（此步不弹窗）
- [ ] 已询问今日目标 N；--show-config 已展示并经用户确认（含折算公式与弹窗位置）
- [ ] 搜索→筛选已循环到可投≥N 或源耗尽（ROUND new_candidates<2），未超额
- [ ] 勾选前已批量拉详情，最终表含硬条件标；用户在已核实表上勾选
- [ ] 招呼语已逐条确认；定制简历只落盘
- [ ] dry-run 通过后才 --execute；execute 后已 --verify，台账含逐岗核实
- [ ] 台账与跟进已汇总
```

命令里的 `scripts/boss/` 相对本技能目录。`$VENV` = `~/.poseidon/outreach/.venv`。

### 第一步：登录、目标、确认参数

1. `$VENV/bin/python scripts/boss/login.py --check`。失效则先问完弹窗位置并写入 config，再 `login.py` 扫码（弹窗，10 分钟超时）——不要先弹到 Chrome 记住的位置再问。cookie 库读失败是退出码 1，不要当成未登录去重扫
2. 问「今天希望投几条」。没给 N 就停下，不要假设
3. 打印并等待确认（不要静默沿用上次配置）：

```bash
$VENV/bin/python scripts/boss/filter.py --show-config
$VENV/bin/python scripts/boss/filter.py --plan-target <N>
```

展示 `CONFIG_CONFIRM`（时薪/日薪/月薪折算、`headed`、`hoursPerDay`、`salaryFloorDay`、`degreeFloor`、`experienceYears`、弹窗位置）和 `TARGET_PLAN`。出现 `CONFIG_MISSING` 先补问写回，不要把退出码或其它输出当成已确认。用户要改就改 `config.json` 再复述。`hoursPerDay` 必须是用户自己的数，不得默认 8。

弹窗位置和上面一起问，不要留到搜索之后。转述时单独问「浏览器弹窗位置要调整吗」，并给出 `windowPosition`、`chromeRemembered`、`windowPresets`。`chromeRemembered` 在左上角（如 0,30）是负坐标被夹回来后记住的，不是用户选过的位置，要说清楚。用户没回答之前不要 `--ack`，也不要搜索。要调整才运行（不要代选角落）：

```bash
$VENV/bin/python scripts/boss/filter.py --set-window 右下
# 或 --set-window 1200,80
# 或 --set-window 1200,80 900x700
# 左侧副屏的负坐标必须写成 --set-window=-1800,80（空格后的负号会被当成另一个参数）
# 取消固定位置：--set-window clear
```

写完再 `--show-config` 复述。用户明确说不调整，或调整后确认整份配置，才：

```bash
$VENV/bin/python scripts/boss/filter.py --show-config --ack
```

不得代确认，不得在确认前加 `--ack`。第五步不再单独问 `headed` 或弹窗位置。

### 第二步：搜索到目标或源耗尽

`TARGET_PLAN` 的 6% 是详情复核前的抓取→可投转化，只用于决定加几页。详情复核后可投会下降；不够就再开一轮，不要为凑 N 放宽日上限或对全部候选开详情。

每一轮：

```bash
$VENV/bin/python scripts/boss/search.py --config
$VENV/bin/python scripts/boss/filter.py --table --merge-rounds --new-only
```

- 不要自定义 `--out`，否则同日快照对不上、去重失效。加页：`search.py --config --pages <更大>`。换关键词先问用户，不要自行加「远程办公」
- stdout 末行 `RESULT ... stopped=... fetched=...`。`captcha`/`blank` 停，让用户处理；`no_api` 见故障排查
- `ROUND new_candidates=<n>`：连续一轮 `<2` 即源耗尽，停搜并汇报「累计可投 Y/N」。`new_boundary` 不计入这条停机线
- 这一轮的表只用来决定要不要加页，**不要拿给用户勾选**。评分读 TSV，不要读 `jobs`/`candidates` JSON。标准见 `references/matching.md`。列表可投仍远小于 N 时，阈值可从 70 降到 65 **一次**
- 列表可投达到 N，或 `TARGET_PLAN` 的页数已经抓完，就进入第三步。投递计划最终不得超过 N

### 第三步：详情前置，再出最终表

硬条件（211/985、工时窗口、招聘截止、HR 活跃）只在详情页。列表分是上界，不能当最终表给用户勾。

1. 用初表圈出拟推荐的 `min(N, 8)` 条，加上可能被勾选的「值得看」边界。不要包含 `ABANDON` 组，也不要对全部候选开详情。超过 12 条先问
2. 一批、一个浏览器会话：

```bash
$VENV/bin/python scripts/boss/detail.py --links <id>,<id>,...
```

`id` 用表里的 id 即可。`BATCH stopped=captcha|blank` 时停，不要改成一岗一进程。
3. 再跑 `filter.py --table --merge-rounds`（不要 `--new-only`）。标记列里的 `school_211` / `time_window` / `weekly_days` / `weekly_hours` / `degree_master` / `dead_post` / `near_floor` / `degree_above` / `exp_short` 以脚本为准，不要重新心算薪资。`dead_post` 不进推荐。截止过期但 HR 近期活跃的，标注后交用户（`references/matching.md`）
4. 出最终表，等用户勾选。复核后可投仍 < N、且上一轮 `new_candidates≥2`：回到第二步加页或问过用户再换关键词，不要为凑数放宽日上限。`autoConfirm=true` 时只展示，仍不超额

### 第四步：物料

对勾选岗位：招呼语按 `../gen-greeting/references/greeting-principles.md` 与 `../gen-greeting/references/greeting-templates.md` 生成，**不要为写招呼语联网**。JD 用已落盘的 `detail-<id>.json`。单个岗位可调 `gen-greeting`；超过 5 个就直接读那两个文件批量写。未标注居家/远程的岗位，招呼语里加一句询问能否远程；**不要写每天几小时**。

定制简历只对用户指定的岗位（默认可投里的 top 3）按 `create-resume` 做关键词与排序微调，存 `resumes/<公司>-<岗位>.md`，不虚构。PDF 用 `convert-md`。`apply.py` 不发送附件，计划里不要写 `resume`。

计划存 `~/.poseidon/outreach/boss/plan-<batch>.json`：

```json
{"batch":"<日期>-<关键词>","jobs":[{"link":"https://www.zhipin.com/job_detail/<id>.html","job":"...","company":"...","greeting":"必填"}]}
```

展示「岗位 × 招呼语」全文，逐条确认后才投。条数 ≤ N。

### 第五步：投递

`headed` 和弹窗位置都以已确认的 config 为准，这里不再问。`headed=true` 时两条命令都加 `--headed`。

```bash
$VENV/bin/python scripts/boss/apply.py --plan <plan路径>
$VENV/bin/python scripts/boss/apply.py --plan <plan路径> --execute
```

dry-run 不打开聊天层。首次 execute 少量「未找到聊天输入框」：会话可能已建立（平台代发了默认招呼），说明后 `--execute --retry` 补发（按聊天记录去重）。大面积 `no_input` 且 diag 的 `pages[].bodyTextHead` 停在详情初始态：是频控弹层，不是选择器问题，冷却后 `--execute --retry`。`COOLDOWN_REQUIRED` 由脚本 sleep，不要中断、不要另找绕过参数。

`--execute --retry --limit N` 只处理计划前 N 条。结果文件带时间戳。`sent` / `already_connected` / `skipped` / `no_button` / `error`；`stopped=captcha|daily_limit` 时说明原因和截图位置。

### 第六步：核实与台账

execute 之后**必须**跑核实，批次才算结束。它和 execute 共用冷却预算：

```bash
$VENV/bin/python scripts/boss/apply.py --plan <plan路径> --verify
```

只读：仅「继续沟通」才进会话，绝不点「立即沟通」。脚本把逐岗 `verifyStatus` 写回 `delivered.json`；汇总里每条 `sent` 仍要有对应核实行。execute 的 stdout 会出现 `VERIFY_REQUIRED`，看到就接着跑，不要当成可选。`missing` / `in_editor` 用 `--execute --retry` 补，不要对用户说已送达。

汇总公司/岗位/招呼语要点/时间/核实状态。新会话两条消息是正常的：平台默认招呼在上，定制招呼在下。跟进时把回复写回台账，不要只留在对话里：

```bash
$VENV/bin/python scripts/boss/apply.py --set-reply <岗位id> read
```

状态：`unread` / `read` / `replied` / `no_reply`。24h 内回复概率最高；已读不回可用 `gen-greeting` 的跟进模板。

## 故障排查

| 现象 | 处置 |
|------|------|
| `CONFIG_MISSING` | 补问后写回再跑。`hoursPerDay` 不得默认 8 |
| `WINDOW_POSITION_INVALID` | 坐标离屏或不成对。用 `--set-window` 的预设或屏幕内坐标，不要写 -32000 |
| `LOGIN_EXPIRED` | `login.py` 重扫。`--check` 退出码 1 是 cookie 库读失败，不是过期 |
| `stopped=no_api` | 未登录或风控；反复出现则按 `references/boss-zhipin.md` 更新 `map_job` |
| `captcha` | 降 `dailyLimit`、拉大 `delaySec`、冷却；`--headed` 人工过验 |
| `COOLDOWN_REQUIRED` | 脚本在冷却，等它结束。不要中断，没有跳过参数 |
| execute 大面积 no_input，`pages[].bodyTextHead` 停在详情初始态 | 会话未建立（频控），不是选择器。冷却后 `--execute --retry`。diag 顶层是 `{tag, pages[]}`，`bodyTextHead` 在 `pages[]`，`selectorHits` 在 `pages[].frames[]` |
| 用户质疑没发出去 | `--verify`。会话顶部是平台默认招呼，定制招呼是第二条 |

## 参考文件

- `references/platforms.md` — 平台索引
- `references/boss-zhipin.md` — 连接手册（登录/URL/选择器/风控/diag）
- `references/matching.md` — 评分、边界分级、硬条件标

## 合规边界

仅限用户本人账号、本人求职。自动化违反平台服务条款，账号可能被限制，须用户知情。不得用于批量营销、代投或爬取他人数据。
