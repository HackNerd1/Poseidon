# BOSS直聘连接手册

> 最后校准：2026-10（全链路实机验证通过：登录/搜索/详情可达）。
> Boss 前端会不定期改版，本文件 + `scripts/boss/_lib.py` 是唯一需要维护的两处。

## 目录
- 基本判断
- 环境要求
- 登录
- 搜索：接口拦截
- 城市代码
- 详情页与聊天
- 维护指引
- 频控与风控
- 已知怪癖
- 合规与风险

## 基本判断

- **无公开 API**：直接调 wapi 需要 `__zp_stoken__` 加密参数 + geetest，脚本直连不可行
- **可行路径 = 真实浏览器 + 接口拦截**：Patchright 驱动真实 Chrome 复用真人登录态，页面自己请求的数据接口（`joblist.json`）用 `expect_response` 拦截取明文——绕开 DOM 字体反爬，字段比 DOM 更全
- **引擎必须用 Patchright**：原生 Playwright（含 channel=chrome + 直连 + 清新 profile）均被风控识别——登录页加载后几秒被打成空白页；根因是 CDP 协议特征可被页面 JS 探测。get_jobs 同样从 Playwright 迁移到 Patchright。脚本经 `_lib.sync_pw()` 只使用 patchright；未安装直接失败，不退回 Playwright
- **沟通即投递**：没有「投递简历」独立动作，点击「立即沟通」发招呼语即完成触达；附件简历在会话中按需发送
- **必须本机运行**：服务器/机房 IP 直接被识别；本机代理需绕过（脚本已内置 `--no-proxy-server`）

## 环境要求

- **必须直连**：系统代理/Clash 出口（境外或机房 IP）命中风控——症状是登录页先正常加载、几秒后整页被打成空白（`about:blank`）。若用户开 TUN 模式（全局接管），脚本绕不过，须手动关
- **真实 Chrome 通道**：脚本 `channel="chrome"` 优先用本机 Chrome；捆绑 Chromium 的内核版本与 UA 存在 `userAgentData` 指纹矛盾，检测风险更高
- **后台运行 = 屏幕外隐藏窗口，而非无头**：无头模式响应体被跳转销毁且 patchright 对 headless 不做反检测补丁；屏幕外定位（`--window-position=-32000,-32000`）实测 `visibilityState=visible`/`hasFocus=true` 与前台完全一致，指纹无差异。脚本默认隐藏窗口后台跑，`--headed` 才显示窗口（登录必显）
- **验证码是频次累积信号**：同 profile 短时间高频访问会升级出 geetest 图形题（与窗口位置无关）。处置：`--headed` 人工过验。搜索页 headed 时等待 joblist 最长 180s，期间可过验；投递遇到验证码立即停止，不会再等。冷却几分钟、降频次
- **空白页防护**：`goto_guarded()` 统一包装导航，跳白自动重试 2 次（截图留证），仍失败返回诊断文案。触发时排查：确认装了 patchright → 关代理/TUN → 换网络 → 稍后再试
- **profile 污染**：一次被标记的风控事件会让 profile 的安全 cookie 被拉黑，之后换浏览器换网络都无效。处置：`rm -rf ~/.poseidon/outreach/boss/profile` 重新扫码

## 登录

- 扫码登录，登录态 cookie `wt2`，实测约 **7 天** 有效
- 登录页默认停在短信验证码标签，`login.py` 自动切「APP扫码登录」；二维码约 2-3 分钟过期，脚本自动点「点击刷新」
- 检查方式：`login.py --check` 只读 profile 里的 `wt2`（`Default/Cookies`），不启动浏览器。扫码流程里仍用 `_lib.has_login`。登录态存 `~/.poseidon/outreach/boss/profile/`

## 搜索：接口拦截

**数据源**：SPA 加载搜索页时自己 POST `https://www.zhipin.com/wapi/zpgeek/search/joblist.json`，响应 `zpData.jobList[]` 为明文结构化数据（**无字体反爬**）。脚本用 `page.expect_response` 确定性等待（sync 模式禁止在 response 回调里取 body，会死锁——必须等 context 退出后取）。

**分页 = 无限滚动**：滚到底部 SPA 自动 POST 下一批（每批 15 条，`zpData.hasMore` 标记是否还有）。**URL 的 `page` 参数被 SPA 无视**（page=2 仍返回第 1 批），勿用。

**字段映射**（`search.py:map_job`，jobList 原始字段 → 统一 schema）：

| 原始字段 | 含义 | 映射 |
|---------|------|------|
| `encryptJobId` | 岗位 ID | `id` / `link`（`/job_detail/<id>.html`） |
| `jobName` / `salaryDesc` | 岗位名 / **明文薪资**（`15-25K·13薪`） | `job` / `salary`+`salaryParsed` |
| `brandName` / `brandIndustry` / `brandScaleName` / `brandStageName` | 公司 / 行业 / 规模 / 阶段 | `company` / `industry` / `scale` / `stage` |
| `bossName` / `bossTitle` / `bossOnline` | HR 姓名 / 头衔 / **是否在线** | `hr` / `hrTitle` / `hrOnline`（列表没有活跃天数） |
| `goldHunter` | **猎头岗标记** | `goldHunter` |
| `skills` / `jobLabels` / `welfareList` | 技能 / 要求标签 / 福利 | `skills` / `tags` / `welfare` |
| `jobExperience` / `jobDegree` | 经验 / 学历要求 | `experience` / `degree` |
| `cityName` / `areaDistrict` / `businessDistrict` | 市 / 区 / 商圈 | `area` |
| `securityId` | 详情接口凭证 | `securityId` |
| `jobValidStatus` | 岗位有效性 | `jobValid` |

**字体反爬说明（为何不走 DOM 抓列表）**：搜索卡片（新版 `li.job-card-box`）的薪资数字是 PUA 私有区字符（U+E032-E03A），靠 `kanzhun-mix` 自定义字体渲染成数字，`textContent` 拿到的是不可见字符；公司名/地区节点类名也随新版改成了 `.boss-name`/`.company-location`。解码字体成本高且脆，接口拦截一次性解决。

## 城市代码（常用）

| 代码 | 城市 | 代码 | 城市 |
|------|------|------|------|
| 100010000 | 全国 | 101210100 | 杭州 |
| 101010100 | 北京 | 101270100 | 成都 |
| 101020100 | 上海 | 101200100 | 武汉 |
| 101280100 | 广州 | 101110100 | 西安 |
| 101280600 | 深圳 | 101190400 | 南京 |

完整表：`wapi/zpgeek/common/data/city/site.json`（页面自己会请求，可拦截获取）。

## 详情页与聊天（apply.py 使用，dry-run 已验证按钮可达）

| 元素 | 选择器（多候选兜底） |
|------|---------------------|
| 立即沟通 | `a.btn-startchat`（兜底 `a[ka='job_detail_chat']`、text 匹配） |
| 已沟通过 | 同位置按钮文字变「继续沟通」→ 打开会话后按聊天记录内容去重补发，不重发已有内容 |
| 聊天输入框 | `#chat-input`（contenteditable div；兜底 `.chat-input textarea`、`[contenteditable='true']`）。2026-10-20 复测：点「继续沟通」后当前标签页 SPA 跳 `/web/geek/chat` 路由，输入框在主 frame 约 1s 可见；探测必须跨标签页×iframe（`_lib.find_chat_input`） |
| 发送按钮 | `button.btn-send`（初始 disabled，输入后启用；兜底 text=发送 / 回车。发送后以聊天记录校验为准，用 `_lib.history_text`——整页文本减输入框文字，「打了没发出去」不算已发送，防假阳性 sent） |

详情页（2026-10-19 实测，旧说法已过时）：新版详情页**不再请求** `job/detail.json`，岗位数据走 SSR，直接在 DOM `innerText` 里。可提取：完整 JD、兼职条款（工作周期/每周工期/结算方式/招聘截止时间）、HR 活跃时间。活跃时间是 boss 名下一整行（`刚刚活跃`/`本周活跃`/`半年前活跃` 等），**列表接口 joblist.json 没有这个字段**（只有 `bossOnline` 布尔）。注意页面固定按钮「完善在线简历」含「在线」二字，正则必须整行匹配，不能子串搜「在线」。`detail.py --link <岗位链接>` 即按此提取并落 `detail-<id>.json`（`hrActivity`/`terms`/`jdText`，`rawText` 兜底全文——标签没识别到时先看它）。

## 维护指引（Boss 改版后）

1. **搜索抓取异常**：先区分层级——接口没拦到（`stopped=no_api`）→ 登录/风控问题；接口有数据但字段错 → Boss 改了字段名，对照本手册「字段映射」更新 `map_job`；分页失效 → 确认还是无限滚动（滚动触发 POST `page=N`）
2. **投递链路异常**（`no_button`/找不到输入框）：本机浏览器打开岗位详情页，DevTools 查按钮新类名，更新 `_lib.SEL` 的 `detail`/`chat` 多候选数组首位（旧的保留兜底），并同步本手册。输入框找不到时先跑跨 frame/标签页探测（`find_chat_input`），apply 的 no_input error 会在 `boss/diag/chat-*.json` 落每个 frame 的候选选择器命中数与正文头部，先读它再改 SEL（截图没法被脚本回读）；`is_visible(timeout=)` 不等待，别用它做出现等待
3. **页面结构大改**（如详情改双栏 SPA 内嵌）：详情可拦截 `job/detail.json`，聊天弹层选择器重新探测；若接口加密升级则回退 DOM + 字体解码方案（社区有 kanzhun 字体映射脚本可参考）

## 频控与风控

**平台限制：**
- 打招呼日上限约 **100 次**（会员更高）。触顶页面出现「今日沟通人数已达上限」
- 本技能默认 `dailyLimit=50`（平台上限的 50%），`delaySec=[8,20]`，每 10 个长休息 1-3 分钟——触发风控时先调低这三项

**风控信号（出现任一 → 立即停止批次，截图，转人工）：**
- 「安全验证」滑块（geetest）——导航后/点击沟通后/发送后三个时机都检测
- 「异常操作」「访问环境异常」提示
- `stopped=no_api` / 反复空白页

**降低风控的实践（get_jobs / jobclaw / boss-autogreet 共识 + 本次实测）：**
- Patchright 引擎 + 真实 Chrome 通道 + 有头模式；`--disable-blink-features=AutomationControlled`
- 直连（`--no-proxy-server`）；绝不服务器部署；避开深夜/整点批量跑
- 逐字符输入（30-90ms/字符）、随机延迟、人类式滚动
- 已沟通（「继续沟通」）岗位绝不重发
- **同日多次浏览器会话是弹层诱因**（2026-10-20 实测）：搜索 + 4×详情 + dry-run + execute 累计 4+ 次会话后，execute 首跑 13/13 报 no_input，diag 的 bodyTextHead 显示页面全停在职位详情初始态（会话未建立）；冷却 150s 后 `--retry` 11+1 成功、弹层消失。同日第二轮 execute 前主动冷却 ≥3 分钟；症状出现时不要排查选择器

## 已知怪癖

1. **默认招呼语自动发送**（2026-10-20 复测）：首次点击「立即沟通」后 Boss 先用账号预设默认招呼语开聊（如「你好，我对这个职位很有兴趣…」），定制招呼语需再发一条。当日事故：`apply.py` 连续 5 岗报「未找到聊天输入框」，根因是 `find_visible` 用 `is_visible(timeout=)`（瞬时检查、不等待）且只扫单一 page/frame，SPA 跳路由后探测全落空。已修：`wait_for` 真等待 + `find_chat_input` 跨标签页/iframe 全量探测；已沟通岗位改为打开会话后按「聊天记录是否已含本条招呼语」去重补发，`--retry` 可重处理失败批次。投后核实用 `apply.py --verify`（只读，逐岗比对 `in_history`/`in_editor`）
2. **URL page 参数无效**：SPA 分页只认滚动触发，构造翻页 URL 没用（实测 page=2 仍返回第 1 批）
3. **兼职筛选**：搜索 URL 加 `&jobType=1903` 即只出兼职岗（SPA 会带进 joblist POST；响应 `jobType=6` 为兼职、`0` 为全职）。`search.py --job-type` / `config.jobType` 已支持。兼职薪资常为「元/天」「元/时」（2026-10-20 实测 160 条兼职里计件占 100%），`parse_salary` 已支持元/时、元/天、元/周、元/月四类（含单值如「200元/天」）；折算成时薪/日薪与 `belowFloor` 标记由 `filter.py` 完成，`hoursPerDay` 必须来自用户确认过的 config，不得默认 8 小时。旧快照里残缺的 `salaryParsed` 会被 `filter.py` 重新解析覆盖，无需重搜
4. **`is_captcha` 全文误报**：详情页 JD 正文提到「验证码」会被旧版全文正则判成风控（赛琳贸易岗实测）。详情/聊天页改用 `is_captcha_strict`（只认 geetest 面板或「安全验证/异常操作/访问环境异常」弹层文案）；搜索页仍用全文版
5. **附件简历**：会话中可发附件/图片简历；get_jobs 实践表明「打招呼后自动发图片简历」回复率更高，自动化发送未经本脚本验证（接入选做）
6. **僵尸岗**：列表只有 `bossOnline` / `hrOnline`，没有「上次活跃」，不要按天数过滤。活跃时间只在详情页 DOM，筛僵尸岗必须逐岗打开详情页
7. **猎头岗**：`goldHunter=1` 直接标记，筛选阶段默认归零或按用户配置处理；HR 头衔含「招聘顾问/猎聘」也提示人工留意

## 合规与风险

自动化操作违反 BOSS直聘用户协议，存在限流、临时封禁乃至封号风险。本技能的频控参数即为此设计的下限保障，但**风险无法归零**，是否使用由用户自行决定。仅限本人账号本人求职，禁止商用代投与批量营销。
