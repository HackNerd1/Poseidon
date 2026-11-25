# 需求：岗位聚合平台（feeds）— auto-apply 多平台岗位入口

> 状态：需求记录，待实现
> 提出日期：2026-11-11
> 关联 skill：`plugins/outreach/skills/auto-apply`（BOSS直聘入口已上线，本文档为其扩展岗位入口）

## 1. 背景与调研结论（2026-11-11 实测）

auto-apply 目前仅支持 BOSS直聘（浏览器自动化）。为增加 V2EX、电鸭、Upwork 等入口，调研了"订阅新发布岗位"的现成数据源，结论：

### 1.1 可直接消费的数据源（实测可用，无需登录）

| 源 | 端点 | 关键特性 |
|----|------|---------|
| **remotecn.com**（V2EX t/1190751，个人聚合站） | `GET https://remotecn.com/api/jobs?keyword=x&workType=parttime&regionLimit=CN&page=N&limit=50` | 404 岗位，**每日爬取**；字段全：`contentHash/datePosted/applyUrl/description(markdown)/sourceSite/isActive/regionLimit/workType/category/tags`；来源覆盖**电鸭(63/首100)+remote.com+realworkfromanywhere+rebase+阮一峰周刊**；**服务端搜索可用**：`keyword=`（中文子串、大小写不敏感，2026-11-11 实测）+ workType/regionLimit 可叠加，`sort=datePosted` 降序；⚠️ `q/query/search/kw` 参数被忽略；无 RSS；个人项目，有停更风险 |
| **V2EX 酷工作**（官方 Atom） | `https://www.v2ex.com/feed/jobs.xml` | 最新 50 条 ≈ 2 天窗口，**全文含联系方式**；`?p=2` 无效；勿用 `feed/tab/jobs.xml`（混灌水帖） |
| **电鸭社区**（公开 JSON API） | `https://svc.eleduck.com/api/v1/posts?category=5&sort=-published_at&page=N`；详情 `posts/{id}` | 25 条/页，可深分页补漏；tags=全职远程/线上兼职/城市；**必须带 `sort=-published_at`**（默认非时间序）；category 22=人才库、23=Upwork 话题 |
| 海外远程聚合站 | Himalayas `/jobs/rss` + `/jobs/api`；Jobicy API v2；RemoteOK API；WWR 分类 RSS；Working Nomads RSS | 英文为主，与 remote.com 数据重叠，去重后可选订 |

### 1.2 已验证不可行 / 替代方案

- **Upwork 官方 RSS 已下线**（410 Gone）；curl / headless 全被 Cloudflare 403；**patchright headed 模式实测 200**，搜索页 `[data-test='JobTile']` 可解析 → 走 boss 式浏览器方案，proposal 只做草稿不自动提交（connects + ToS 限制）
- 第三方 Vollna（$16–24/mo）提供 Upwork 匹配+RSS 通知，不需要 Upwork 密码，备选
- RSSHub 公共实例全被 Cloudflare 拦（403/503）；对 V2EX/电鸭无必要（官方接口更稳）
- Indeed / StackOverflow Jobs RSS 已停；Freelancer RSS 无关键词过滤
- 聚合站 API 的服务端搜索参数**多数不生效**（Remotive `search=`、Jobicy `tag=`、Himalayas `companyName=` 实测均被忽略；例外：remotecn `keyword=` 生效）→ 筛选仍以本地做为主
- 前人聚合项目参考：easynomad.cn（活，人工精选，无接口）；aab0/awesome-jobs（120★，**2026-01 起停更**，维护成本前车之鉴）；BRIX Telegram Bot（无接口）

## 2. 需求

> **进度更新（2026-11-11）**：用户决策调整——skill 侧不落本地库、不做订阅状态，**直接 API 搜索现拉现用**（"数据不用存本地"）。remotecn 渠道已实现：`scripts/remotecn/search.py` + `references/remotecn.md`。下述自建聚合平台保留为后续需求（M2），skill 侧现状已满足日常使用。

### 2.1 自建聚合平台，单独部署（后续需求）

不把采集逻辑塞进 skill：平台作为**独立部署的服务**，负责多源采集、归一化、去重、存储与查询。

**平台侧职责：**

1. 多源采集（首批：remotecn API、V2EX Atom、电鸭 API；后续可扩展 Himalayas/WWR）
2. 归一化为统一岗位 schema（见 2.3），`contentHash`（remotecn 提供）/ 平台 id 做去重键
3. 生命周期管理：源站下架（remotecn `isActive=false`、帖子删除）→ 标记过期不删行；超期岗位（默认 30 天）归档降权
4. 7×24 定时采集（服务器 / GitHub Actions cron），**每个源独立启停、失败隔离**，单源挂掉不阻塞其余
5. 对 skill 输出统一 HTTP API（分页 + 可选过滤），并保留逐源数据以支持兜底切换
6. V2EX 2 天窗口是唯一必须 7×24 采集的源；remotecn/电鸭可深分页补漏

**部署形态（二选一，倾向前者）：**

- 轻量：任意 VPS / 容器，cron + SQLite/文件存储 + 一个只读 API
- 零服务器：GitHub Actions 定时跑同一份 fetch 代码，结果 commit 回私有 repo

### 2.2 skill 侧：env 配置订阅源

auto-apply 从环境变量读取 feeds 配置，**不硬编码源清单**：

```bash
# 聚合平台 API 地址（无配置则 feeds 功能不可用，降级提示，不报错）
OUTREACH_FEEDS_API=https://feeds.example.com
# 可选：API 鉴权
OUTREACH_FEEDS_TOKEN=
# 本会话启用的订阅源（逗号分隔，空=全部启用源）
OUTREACH_FEEDS_SOURCES=remotecn,v2ex,eleduck
```

- 配置缺失/服务不可达：SKILL.md 引导用户先部署或改走平台搜索入口，不中断 BOSS 流程
- 投递会话开始时先拉一次增量（`--now` 语义），保证新鲜度；平台侧定时采集只负责兜底
- skill 内仍保留**直连兜底 adapter**（V2EX/电鸭官方接口）：聚合平台停更时降级，不影响可用性

### 2.3 归一化 schema（对齐 boss 快照，下游评分/招呼语/台账复用）

```json
{"source": "remotecn", "sourceId": "9644", "title": "...", "company": "...",
 "url": "...", "applyUrl": "...", "workType": "parttime", "region": "CN",
 "tags": ["frontend"], "descriptionMd": "...", "datePosted": "2026-11-10",
 "firstSeen": "...", "active": true}
```

- 台账 `delivered.json` 按平台分 key 防重投（platforms.md 既有约定）
- 投递通道按源区分：V2EX 多为邮箱/微信（从帖文提取联系人，生成草稿人工发送）；电鸭站内私信（可浏览器自动化，人工确认制不变）；Upwork 只做发现+草稿

## 3. 边界与非目标

- 聚合平台**只做采集与查询**，不做评分/招呼语/投递——判断留给 skill
- 不做公开服务给别人用（前人停更案例：awesome-jobs）；数据仅自用
- 不订阅 BOSS/猎聘等强反爬平台进 feeds（走既有浏览器方案）
- 本地方案（skill 内直连）作为**长期保留的降级路径**，不是被替代的过渡方案

## 4. 里程碑（建议）

1. **M1 ✅（2026-11-11）**：remotecn 直连搜索已实现（`scripts/remotecn/search.py`，纯查询不落库，keyword/workType/region/days 过滤 + TSV 出表）；V2EX/电鸭直连 adapter 待做
2. **M2**：抽成独立服务单独部署（API + 定时采集 + 故障隔离），skill 切 env 配置（`OUTREACH_FEEDS_API/SOURCES`）
3. **M3**：Upwork 浏览器入口（headed patchright，只做发现+草稿）
4. **M4（可选）**：扩源（Himalayas/WWR）、GitHub Actions 零服务器形态
