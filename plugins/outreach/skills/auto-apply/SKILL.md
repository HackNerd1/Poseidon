---
name: auto-apply
description: 自动投递简历工作流：按用户简历与求职偏好，在招聘平台搜索岗位 → 智能筛选 → 生成打招呼语 → 按JD定制简历 → 执行投递。当前支持 BOSS直聘（Patchright 驱动本机 Chrome，扫码登录，频控+验证码人工介入）。当用户要求"自动投递简历"、"批量投简历"、"自动打招呼"、"boss直聘投递"、"筛选岗位并投递"时触发。仅限用户本人求职使用，默认人工确认制。
---

# 自动投递简历工作流（auto-apply）

## 概述

编排器角色：脚本负责浏览器 I/O（登录、搜索、投递），Claude 负责判断（筛选评分、打招呼语、简历定制）。串联 `gen-greeting` 与 `create-resume` 两个技能，完成「搜索 → 筛选 → 物料 → 投递 → 台账」闭环。

**四条红线：**
1. **默认人工确认**：筛选结果和最终投递都必须经用户确认后才执行（`config.autoConfirm=true` 才可跳过，且仍要展示将投清单）
2. **频控保守**：日上限默认 50（平台约 100），随机间隔 + 批次长休息；触平台上限立即停
3. **验证码即停**：任何环节出现安全验证/滑块，停止批次、截图留证、转人工，绝不自动过验
4. **台账防重**：同岗位 7 天内不重投（`delivered.json`）；不虚报简历内容

## 数据目录

所有状态存 `~/.poseidon/outreach/`（可用 `OUTREACH_DATA_DIR` 环境变量覆盖）：

```
~/.poseidon/outreach/
├── .venv/                  # Python 虚拟环境
├── config.json             # 求职配置（城市/关键词/黑名单/频控/兼职折算参数）
└── boss/
    ├── profile/            # 浏览器登录态（扫码一次约 7 天有效）
    ├── jobs-<日期>.json     # 搜索快照（原始全量，本地留存，不必进对话）
    ├── candidates-<日期>.json # 预过滤候选+边界（筛选打分只读这个）
    ├── screen-<日期>.json   # 筛选审计（每条去向与淘汰统计，调阈值时才读）
    ├── detail-<id>.json    # 岗位详情（JD 全文/兼职条款/HR 活跃）
    ├── plan-<批次>.json     # 投递计划（Claude 生成）
    ├── plan-<批次>.result-<时间戳>.json
    ├── delivered.json      # 投递台账
    ├── diag/               # 投递找不到输入框时的选择器命中明细
    ├── resumes/            # 定制简历产出
    └── screenshots/        # 风控/异常留证
```

## 首次使用

```bash
VENV=~/.poseidon/outreach/.venv
python3 -m venv $VENV
$VENV/bin/pip install -r scripts/requirements.txt
# 需要本机已安装 Google Chrome。脚本用 channel=chrome，不安装、不使用捆绑 Chromium。
# 未安装 patchright 时脚本直接失败，不退回 Playwright。
$VENV/bin/python scripts/boss/login.py    # 弹窗扫码，10 分钟超时
```

配置 `config.json`（不存在时与用户交互式收集后写入）：城市代码（见 `references/boss-zhipin.md`）、搜索关键词（用岗位词如「前端/Electron」，不要用「远程办公」这类属性词——只会引来讲师/主播岗）、期望薪资、经验年限、黑名单公司/关键词、每日上限、**浏览器窗口**（`headed`：前台显示 / 后台隐藏）。搜兼职（`jobType=1903`）时必须再问两项写回：`hoursPerDay`（每天工作几小时，**必须问用户本人，不得默认按 8 小时折算**）和 `salaryFloorDay`（日薪下限）。`headed` 在这一步定死，搜索和投递都读它，之后不再询问。旧配置缺这些字段时，`search.py --config` 会以 `CONFIG_MISSING` 拒绝并列出缺什么，在本步补问写回即可；config.json 里残留的 `skipInactiveDays` 是死配置，脚本会打印 IGNORED 并忽略。

## 工作流

复制这份清单到回复里，做完一项勾一项：

```
投递进度:
- [ ] login.py --check 已确认登录态（此步不弹窗）
- [ ] 搜索参数已向用户复述（关键词 × 城市 × 页数 × headed）
- [ ] 搜索结果已展示，stopped 已检查
- [ ] 筛选表已出，用户已勾选（autoConfirm 也要展示清单）
- [ ] 招呼语已逐条确认；定制简历只落盘，本次不发送附件
- [ ] dry-run 通过后才 --execute
- [ ] 台账与跟进已汇总
```

### 第一步：准备与登录

1. 检查 `.venv` 与登录态：`$VENV/bin/python scripts/boss/login.py --check`
2. 失效则运行 `login.py` 让用户扫码（弹窗，10 分钟超时）
3. 读取/创建 `config.json`，向用户复述本次搜索参数（关键词 × 城市 × 页数 × 是否前台 `headed`）。`headed` 缺失则在这里补问并写入，不要留到第五步

### 第二步：搜索岗位

```bash
$VENV/bin/python scripts/boss/search.py --config
# 或临时参数: $VENV/bin/python scripts/boss/search.py --query "golang" --city 101280600 --pages 2
```

读取输出 JSON（stdout 末行 `RESULT <路径>`），检查 `stopped` 字段：`captcha`/`blank` → 停止让用户处理后重试；`no_api` → 见故障排查。数据经 `joblist.json` 接口拦截获取（明文薪资/HR在线/猎头标记/公司行业规模阶段/技能福利标签），字段说明见 `references/boss-zhipin.md`。

搜索成功后立即预过滤（纯本地，不启动浏览器）：

```bash
$VENV/bin/python scripts/boss/filter.py   # 自动取最新 jobs-*.json
```

之后只读 `RESULT` 指向的 `candidates-<日期>.json`（候选 + 边界，计件薪资已折算时薪/日薪并打好 `belowFloor`），向用户展示总数与样例。原始 `jobs-*.json` 留在本地不要读进对话——160 条全量进上下文曾是最大 token 消耗点。淘汰明细在 `screen-<日期>.json`，调阈值时才读。

### 第三步：筛选（Claude 判断）

输入用 `candidates-<日期>.json`：黑名单、猎头、7 天内已投、城市、非兼职、岗位名门禁（老师/主播/销售/剪辑/客服出，开发词进）、同公司同岗位去重已由脚本完成，不要重复执行。按 `references/matching.md` 的评分标准，对候选逐条输出：

```
| 得分 | 岗位 | 公司 | 薪资 | 理由 | 处置 |
```

- `boundary` 边界岗位（`below_floor`/`wide_range`/`hourly_too_high`）不静默丢弃，单独列出交用户决策
- 70 分附近、或日薪/周薪计酬与 `hoursPerDay` 可能不兼容的岗位，先 `detail.py --link <岗位链接>` 拉详情核对「工作周期/每周工期/结算方式」再定；不要对全部候选逐个开详情
- 经验/学历明显不符仍由你判断淘汰，不进表格；`hrOnline=false` 不淘汰（实测候选可能全不在线），不要按活跃天数淘汰
- 展示候选清单，**等用户勾选确认**后进入物料阶段（`autoConfirm=true` 时仅展示）

### 第四步：生成物料

对用户确认的每个岗位：

1. **打招呼语**：按 `gen-greeting` 的本地标准生成（`../gen-greeting/references/greeting-principles.md` + `../gen-greeting/references/greeting-templates.md`），**不要为写招呼语去联网**。已开过详情的岗位用 `detail-<id>.json` 的 JD 全文让证据更具体。单个岗位可调用 `gen-greeting` 技能（该技能默认也不搜索）；批量（>5 个）时直接读上述两个文件批量生成（证据先行、最匹配项前置、超短版 70-80 字优先——适配聊天框），输出写入投递计划
2. **定制简历**：对用户指定的岗位（默认 top 3 或用户全选）按 `create-resume` 技能的 JD 匹配流程，基于原简历生成定制版，存 `resumes/<公司>-<岗位>.md`。**只做关键词与排序微调，不虚构经历**；转换 PDF 用 `convert-md`。文件只落盘。`apply.py` 不读、不发送附件，不要把 `resume` 写进投递计划

生成投递计划文件：

```json
{
  "batch": "<日期>-<关键词>",
  "jobs": [
    {"link": "https://www.zhipin.com/job_detail/<id>.html", "job": "...", "company": "...", "greeting": "必填，缺了脚本不会打开页面"}
  ]
}
```

存到 `~/.poseidon/outreach/boss/plan-<batch>.json`，向用户展示「岗位 × 招呼语」全文，**逐条确认后**才执行投递。

### 第五步：投递

浏览器是否前台显示以 `config.headed` 为准（第一步已确认），**这里不再询问**。`headed=true` 时下面两条命令都加 `--headed`；脚本也会读 config，显式传参只是让本次命令和配置一致。

```bash
# 先 dry-run（只验证岗位可达、按钮存在；未覆盖点击后聊天链路）
$VENV/bin/python scripts/boss/apply.py --plan <plan路径>
# 确认无误后真实发送
$VENV/bin/python scripts/boss/apply.py --plan <plan路径> --execute
```

dry-run 不打开聊天层，首次 execute 出现少量「未找到聊天输入框」error 属预期：会话其实已建立（平台代发了默认招呼语），向用户说明后用 `--retry` 补发即可（已沟通岗位按聊天记录内容去重，不会重发）。结果文件带时间戳（stdout `RESULT` 指向最新一份），重跑不覆盖历史。解读结果：`sent` / `already_connected` / `skipped` / `no_button` / `error`；`stopped=captcha|daily_limit` 时告知用户原因与截图位置。缺 `link` 或 `greeting` 的 `error` 是计划校验失败，没有打开页面；「未找到聊天输入框」的 error 附有 `diag/` 明细路径，排查选择器是否过时用。

### 第六步：台账与跟进

汇总本次投递清单（公司/岗位/招呼语要点/时间），提醒用户：
- HR 回复通常在 24h 内，次日可运行 `gen-greeting` 的跟进模板对「已读不回」跟进
- 建议每次投递后记录回复情况，用于调整黑名单与筛选阈值

## 故障排查

| 现象 | 处置 |
|------|------|
| `CONFIG_MISSING` | 配置缺必须由用户定的字段（`headed`；兼职的 `hoursPerDay`/`salaryFloorDay`）。补问后写回 config.json 重跑，不要用默认值绕过（hoursPerDay 默认 8 小时曾被用户纠正） |
| `LOGIN_EXPIRED` | 运行 `login.py` 重新扫码 |
| `stopped=no_api`（未拦截到数据接口） | 未登录或风控；反复出现则 Boss 改版，按 `references/boss-zhipin.md`「维护指引」更新 `map_job` 字段映射 |
| `captcha` 频繁 | 降低 `dailyLimit`、拉大 `delaySec`、冷却几分钟；`--headed` 在窗口中人工完成图形验证；检查代理（需关闭） |
| 后台运行就触发风控？ | 实测屏幕外隐藏窗口与前台指纹一致（visibilityState 相同），风控与窗口位置无关，多为频次累积——先冷却 |
| 投递后 HR 侧无记录 | 可能触发了默认招呼语机制，见 `references/boss-zhipin.md`「已知怪癖」 |

## 参考文件

- `references/platforms.md` — 各平台连接方式总索引（当前 boss 已实现，其余规划）
- `references/boss-zhipin.md` — BOSS直聘连接手册（登录/URL/选择器/风控/限制/维护指引）
- `references/matching.md` — 岗位筛选评分标准与输出 schema

## 合规边界

仅限用户本人账号、本人求职使用；自动化操作违反平台服务条款，存在账号被限制的风险，须由用户知情选择。不得用于批量营销、代投服务或爬取他人数据。
