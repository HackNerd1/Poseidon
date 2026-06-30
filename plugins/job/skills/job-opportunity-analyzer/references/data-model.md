# Data Model

## Overview

本 skill 的结构化事实源先维持轻量模型，不设计成数据库或多表同步系统。首期只覆盖三个核心实体：

- `CompanyProfile`：城市候选公司池中的公司卡片
- `JobOpportunity`：和岗位机会有关的公开事实
- `CompanySentiment`：社区或新闻里的风评摘要

三类结构统一放在一个 schema 文件 [company-pool.schema.json](/Users/xy/Project/skills/Poseidon/plugins/job/skills/job-opportunity-analyzer/assets/company-pool.schema.json) 中，通过 `$defs` 复用字段定义。这样更适合首期维护：

- 只有一个 schema 入口，便于后续脚本做一致性校验
- 三类实体共享 `SourceRef`，避免重复解释来源字段
- 城市样例只要遵循一个顶层文档结构，就能直接扩展到更多城市

## Asset Layout

结构化事实源放在 `assets/`，首期命名规则如下：

- schema：`company-pool.schema.json`
- 城市样例：`<city>-company-pool.sample.json`
- 未来如需报告样例：`<city>-report.sample.md`

当前已提供杭州样例：

- [hangzhou-company-pool.sample.json](/Users/xy/Project/skills/Poseidon/plugins/job/skills/job-opportunity-analyzer/assets/hangzhou-company-pool.sample.json)

后续扩展规则：

- 一个城市一份样例文件，避免把多个城市混在同一个 JSON 里
- 文件名里的 `city` 使用小写 slug，例如 `hangzhou`、`shanghai`、`shenzhen`
- 如果后续需要区分用途，在城市名后追加用途后缀，例如 `hangzhou-company-pool.curated.json`

## Top-Level Document

城市样例文件的顶层结构固定为：

```json
{
  "schema_version": "v1.0",
  "city": "hangzhou",
  "generated_at": "2026-06-30",
  "companies": [],
  "job_opportunities": [],
  "company_sentiments": []
}
```

字段说明：

- `schema_version`：文件所遵循的 schema 版本
- `city`：当前样例的城市 slug
- `generated_at`：样例整理日期；样例文件允许为空，但建议保留
- `companies`：`CompanyProfile[]`
- `job_opportunities`：`JobOpportunity[]`
- `company_sentiments`：`CompanySentiment[]`

之所以不用更复杂的嵌套结构，是因为主 skill 后续会跨来源补全岗位和风评，同一公司可能有多个岗位和多条风评，拆成三个数组更容易追加和校验。

## CompanyProfile

`CompanyProfile` 对应需求文档第 7 节里的公司卡片。首期字段只保留“筛公司”和“解释为什么进入候选池”所必需的内容：

- `company_id`：稳定主键，供岗位和风评引用
- `name`：公司名称
- `city`：公司主城市
- `tier`：`T1` 到 `T4` 的候选层级
- `official_website`：官网链接，可空缺
- `career_url`：招聘页链接，可空缺
- `known_business`：业务关键词数组，用来解释公司所处赛道
- `employee_count`：公开可得的规模估计；未知时保留 `null`
- `avg_rating`：公开评分的近似值；没有可靠来源时保留 `null`
- `tags`：便于查询和聚类的标签
- `notes`：简短补充说明
- `include_reason`：为什么这家公司被纳入该城市候选池
- `source_refs`：支撑上述事实的来源列表
- `last_verified`：最后核验日期

约束说明：

- `source_refs` 至少 `1` 条，避免“只有结论没有出处”
- `known_business` 至少 `1` 项，避免公司进入池子却没有业务语义
- `employee_count` 和 `avg_rating` 都允许 `null`，因为首期强调保留原始不确定性，而不是强行补齐

## JobOpportunity

`JobOpportunity` 记录“某家公司存在一个与目标岗位相关的机会”，不是完整职位数据库。字段聚焦在求职判断：

- `opportunity_id`：岗位记录主键
- `company_id`：关联 `CompanyProfile`
- `job_title`：岗位名
- `tech_stack`：技术关键词数组，可来自原文或谨慎归类
- `experience_required`：经验要求原文
- `salary_range`：薪资原文
- `job_url`：岗位链接，可空缺
- `source_type`：该岗位的主来源类型
- `match_reason`：与目标岗位匹配的原因
- `salary_match`：`match` / `partial` / `unaligned` / `unknown`
- `risk_flags`：风险标签，例如 `salary_unaligned`
- `source_refs`：岗位事实来源

约束说明：

- `experience_required` 和 `salary_range` 都保留原始文本，避免首期过早标准化
- `salary_match` 用离散状态，不用数值评分，避免制造假精确
- `risk_flags` 可以为空数组，但不建议省略不确定性

## CompanySentiment

`CompanySentiment` 用于沉淀社区和新闻里的风评信号，目标是辅助判断，不是替代事实：

- `sentiment_id`：风评记录主键
- `company_id`：关联 `CompanyProfile`
- `community_source`：社区来源名，如 `v2ex`、`niuke`
- `news_source`：新闻来源名
- `pros`：正向信号
- `cons`：负向信号
- `summary`：平衡后的摘要
- `observed_at`：整理日期
- `source_refs`：风评底层来源

约束说明：

- `summary` 必填，因为主 skill 最终要输出可读结论
- `pros` / `cons` 允许为空，但不能没有 `source_refs`
- 风评只能作为辅助信号，不能单独决定是否推荐

## SourceRef

三类实体都共用 `SourceRef`：

- `source_id`：当前文件内可追踪的来源 ID
- `source_type`：`official`、`job_board`、`school_board`、`industry_list`、`community`、`news`、`manual_note`
- `label`：短标题
- `url`：公开链接；如只有手工笔记，可省略
- `observed_at`：观察日期
- `note`：该来源支撑什么结论

这个共享结构的目的，是让主 skill 在生成报告时可以统一展示事实源，而不用为公司、岗位、风评分别写三套引用格式。

## Versioning Rules

版本维护先采用简单规则：

- `v1.0`：首期稳定字段集合
- 新增可选字段：升级为 `v1.1`、`v1.2`
- 删除字段、改字段语义、改必填规则：升级为 `v2.0`

更新 schema 时同步做三件事：

1. 更新 `company-pool.schema.json` 里的 `schema_version` 说明
2. 更新至少一个城市样例文件中的 `schema_version`
3. 在本文件记录变更原因，避免脚本或主 skill 对字段理解不一致

## Non-Goals

首期明确不做：

- 不设计招聘平台账号、投递状态、消息通知等字段
- 不设计数据库级关联或索引策略
- 不提前定义自动抓取流水线输入输出
- 不把多个城市拼成一份超大总表
