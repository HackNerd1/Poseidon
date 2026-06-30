# Hangzhou Canvas Job Research Issues

Date: `2026-06-30`
Owner: `job:job-opportunity-analyzer`
Status: `open`

## Summary

本次在分析Canvas 相关岗位时，成功确认了少量高相关公司与官方招聘入口，但在“岗位级事实提取”阶段暴露出一组稳定问题：

- 官方招聘站普遍为 SPA / 动态渲染，难以直接抓到职位列表和职位详情
- 搜索引擎结果质量不稳定，中文关键词容易漂移到无关页面
- 招聘平台公开页存在反爬或首屏裁剪，难以稳定提取薪资、年限和岗位文本
- 当前工作流更擅长“发现候选公司”，不够擅长“拿到可投递的具体岗位”

这些问题导致报告可以输出“公司级机会判断”，但很难稳定输出“岗位名 / 城市 / 年限 / 薪资 / 直接链接”。

## Impact

- 无法稳定产出高置信度的 `Opportunity Table`
- `salary` 和 `experience` 字段大面积缺失
- `location` 经常只能确认到公司级，不能确认到团队/岗位级
- 需要大量人工复核，降低 skill 的自动化价值

## Issues

### 1. Official career sites are too JS-heavy

Problem:
- 字节、阿里、群核等官方招聘站大量依赖前端渲染
- `curl` 能拿到首页框架、配置和 bundle，但拿不到稳定的职位结果
- 很多职位数据不直接出现在 HTML，而是运行时请求接口

Observed examples:
- `jobs.bytedance.com`
- `talent.alibaba.com`
- `www.kujiale.com/pub/hr-recruit/social/index`

Impact:
- 只能确认“招聘入口存在”
- 难以抽取具体岗位名、工作地、年限、薪资

Suggested fix:
- 增加浏览器级抓取能力，使用可执行 JS 的抓取方案
- 对常见招聘站做适配器，优先捕获页面请求的职位接口
- 将“抓取官方站职位列表”从通用搜索流程里拆成独立能力

### 2. Search engine queries are noisy for Chinese recruiting intent

Problem:
- 用 `某城市 +画布/白板/编辑器 + 招聘` 这类搜索词时，搜索结果容易漂移
- Bing 结果中多次出现和岗位无关的旅游、百科、城市介绍页面
- 对无限画布这种垂类方向，泛关键词召回精度偏低

Impact:
- 候选公司发现效率低
- 搜索结果需要人工筛噪

Suggested fix:
- 建立更强的关键词扩展和负向词过滤
- 优先使用限定域名搜索，例如 `site:jobs.bytedance.com`、`site:job.youzan.com`
- 为“无限画布”维护专门词库：
  - `whiteboard`
  - `editor`
  - `canvas`
  - `协同文档`
  - `低代码`
  - `页面搭建`
  - `图形/渲染`

### 3. Public recruitment platforms are hard to scrape reliably

Problem:
- BOSS 等公开招聘页返回内容不稳定
- 常见情况是首屏壳页面、脚本框架页或受限内容
- 即使访问成功，也未稳定拿到结构化职位卡片

Impact:
- 无法可靠补充 `salary_text`
- 无法可靠补充 `experience_requirement`
- 第三方平台不能有效承担“字段补全”职责

Suggested fix:
- 不把第三方招聘平台当成主事实源
- 优先从官方站拿职位主记录，再用第三方平台补薪资和年限
- 如要继续支持第三方平台，需要单独评估每个平台的可抓取性和稳定性

### 4. Current workflow is better at company discovery than job extraction

Problem:
- 现有 workflow 能较好完成：
  - 城市候选公司发现
  - 官方站入口确认
  - 产品方向相关性判断
- 但在以下环节能力明显不足：
  - 具体职位发现
  - 职位字段结构化
  - 多来源冲突合并

Impact:
- 报告容易停留在“值得关注哪些公司”
- 难以下钻到“现在应该投哪个岗位”

Suggested fix:
- 将流程拆成两个阶段：
  1. `company discovery`
  2. `job extraction`
- 第二阶段单独实现数据模型与抓取器，不再复用普通 web search 逻辑

### 5. City matching is often only company-level, not team-level

Problem:
- 很多官方站可以确认公司存在、产品相关
- 但难以确认具体团队是否在某城市招人
- 特别是飞书、钉钉这类大平台，某城市招可能只是公司维度布局，不代表目标团队一定在某城市

Impact:
- `location_unaligned` 高频出现
- 容易把“相关公司”误当成“当前某城市机会”

Suggested fix:
- 把 `company in city` 和 `job in city` 明确分开
- 没有岗位级城市证据时，默认标注为 `pending-verification`
- 在表格里增加字段：
  - `company_city_confirmed`
  - `job_city_confirmed`

### 6. Salary and experience data frequently remain unavailable

Problem:
- 官方站常不展示薪资
- 第三方平台抓取又不稳定
- 导致薪资和年限过滤形同虚设

Impact:
- 不能有效支持用户基于薪资/年限做筛选
- `salary_unaligned`、`experience_unaligned` 频繁出现

Suggested fix:
- 在 skill 层明确把这两个字段分成：
  - `required for ranking`
  - `optional when unavailable`
- 当缺失率高时，自动降级为“方向筛选”而不是“精确筛选”

## Root Cause

核心根因不是单点 bug，而是能力边界不匹配：

- 目前主要能力偏 `网页搜索 + 静态抓取`
- 目标任务实际需要 `动态站点解析 + 招聘域名适配 + 职位结构化`

也就是说，问题更偏系统能力缺口，而不只是提示词或单次查询策略问题。

## Proposed Follow-up

### P0

- 为 `job-opportunity-analyzer` 增加“动态招聘站抓取”能力说明
- 在报告中更明确地区分：
  - `company-level evidence`
  - `job-level evidence`

### P1

- 为常见招聘站建立适配器：
  - 字节招聘
  - 阿里招聘
  - 北森招聘站
- 支持从页面请求中捕获职位列表接口

### P2

- 建立 `canvas / whiteboard / editor` 方向专用词库
- 增加更强的搜索路由策略：
  - 先产品相关公司
  - 再官方招聘入口
  - 再具体岗位

### P3

- 为招聘平台补充稳定性评估矩阵
- 决定哪些第三方平台值得继续支持，哪些只保留为弱信号来源

## Acceptance Criteria For Fix

后续修复完成后，至少应满足：

- 对 3 个以上常见招聘站，能稳定拿到职位列表
- 对“某城市 + Canvas 相关方向”，能产出至少 3 条岗位级机会
- 每条机会至少包含：
  - `company`
  - `job_title`
  - `job_url`
  - `location`
  - `source_type`
- 对缺失字段能稳定标注异常，而不是静默失败

## Related Files

- `docs/job-skill.md`
- `docs/requirements/job-opportunity-analyzer.md`
- `docs/requirements/job-opportunity-analyzer-overall-plan.md`
