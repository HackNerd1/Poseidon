# remotecn.com 连接手册

> 面向中国开发者的远程工作聚合站（V2EX t/1190751）。个人项目，无官方 SLA——挂了走降级（见文末）。
> 调研与实测日期：2026-11-11。

## 定位

auto-apply 的 **feeds 直连搜索渠道**：skill 直接调其公开 API 搜索，**数据不落本地库**（用户决策 2026-11-11：不存本地、不留订阅状态，每次搜索现拉）。

## 数据来源与量级

- 站方每日爬取；在招 400+ 条（实测 404，2026-11-11）
- `sourceSite` 来源：`eleduck`（电鸭，占比最大）、`rebase`（who-is-hiring issue）、`rwfa`（realworkfromanywhere）、`remotecom`（remote.com）、`ruanyf`（阮一峰周刊）——即**一个 API 覆盖电鸭+主流英文远程聚合站**
- 不含 V2EX（酷工作）；V2EX 走官方 Atom（后续 adapter，见 platforms.md）

## API

`GET https://remotecn.com/api/jobs`（无需鉴权，无 key）

| 参数 | 值 | 实测 |
|------|-----|------|
| `keyword` | 任意子串，**支持中文**（需 URL 编码） | 生效。大小写不敏感（Python=python）；按词在标题/描述匹配；无结果时 `pagination.total=0`（区别于参数被忽略） |
| `workType` | `fulltime` / `parttime` | 生效 |
| `regionLimit` | `CN` / `worldwide` / `EU` | 生效；CN 含中国境内远程，worldwide 为全球不限 |
| `sort` | `datePosted`（默认即降序） | 生效 |
| `page` / `limit` | 分页；`limit` 实测最大用 50 稳妥 | `pagination.total` / `totalPages` 随响应返回 |

⚠️ 被忽略的参数（勿用）：`q` / `query` / `search` / `kw` 均不生效（原样返回全量）。无日期过滤参数——`--days` 在脚本本地过滤。

### 响应字段（data[]）

`id` / `title` / `company` / `category[]`（fullstack、backend、frontend…） / `tags[]` /
`regionLimit` / `workType` / `sourceSite` / `originalUrl` / `applyUrl`（指向源站 ATS：
greenhouse/lever/ashby 或 eleduck 帖子） / `contentHash` / `description`（**Markdown 全文**） /
`datePosted` / `dateScraped` / `isActive` / `updatedAt`

`company` 常见 `Unknown` 或「外包/远程」类长串，出表时截断展示，判断以 title+description 为准。

## 脚本

`scripts/remotecn/search.py`（纯 stdlib，无第三方依赖）：

```bash
# 服务端关键词搜索；--keyword 可传多次（OR，脚本内去重）
search.py --keyword "前端" --work-type parttime --region CN --days 30 --limit 50
search.py --latest                      # 最新岗位流（按 datePosted 降序）
# 环境变量：REMOTECN_API 可覆盖 API 地址（默认 https://remotecn.com/api/jobs）
```

stdout：TSV 表（`# date type region title company tags applyUrl`）+ 末行
`RESULT matched=<本地行数> total=<服务端命中> pages=<页数> stopped=none`。
退出码：0 正常；2 `CONFIG_MISSING`（未给 --keyword/--latest）；3 API 不可达或响应结构变更。

## 降级策略

站方是个人维护，有停更风险（前例：aab0/awesome-jobs 停更于 2026-01）。它挂掉时：
1. 电鸭帖可直连 `https://svc.eleduck.com/api/v1/posts?category=5&sort=-published_at`（官方公开 API，同量级）
2. 英文聚合站直连 Himalayas `/jobs/rss`、WWR 分类 RSS
3. `FETCH_ERROR` 连续出现时向用户报告并建议换源，不要静默重试多次拖慢会话

## 合规

公开 API、只读、无登录态。搜索频率与人工浏览相当（单次搜索 ≤ 数页），无需频控。
