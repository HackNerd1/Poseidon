---
name: info-schema
description: JSON/YAML 输入文件的字段定义。供 create-resume SKILL.md 主控流程在解析用户数据文件时使用，定义各字段的类型、必填/选填及示例值。适用于所有岗位。
---

# 简历信息输入 Schema

## JSON 示例

```json
{
  "basicInfo": {
    "name": "张三",
    "phone": "138-0000-0000",
    "email": "zhangsan@example.com",
    "github": "https://github.com/zhangsan",
    "blog": "https://zhangsan.dev",
    "portfolio": "https://zhangsan.dev/projects",
    "yearsOfExperience": 4,
    "targetRole": "后端工程师"
  },
  "summary": "4 年后端工程师，深耕 Java 微服务与高并发系统设计，主导过日均千万级请求的支付网关架构。",
  "techStack": {
    "语言/框架": ["Java", "Spring Boot", "Spring Cloud", "MyBatis", "Python"],
    "数据库/缓存": ["MySQL", "Redis", "Elasticsearch", "Kafka"],
    "中间件/基础设施": ["Docker", "Kubernetes", "Nginx", "Prometheus"],
    "测试/工具链": ["JUnit", "Git", "GitHub Actions", "SonarQube"]
  },
  "workExperience": [
    {
      "company": "某科技有限公司",
      "role": "高级后端工程师",
      "startDate": "2021.06",
      "endDate": "2024.03",
      "background": "支付网关核心系统，日均 500 万+ 笔交易，面临高并发场景下的稳定性与一致性挑战。",
      "responsibilities": "负责支付网关架构设计与核心模块开发，主导微服务拆分与分布式事务方案。",
      "highlights": [
        "主导支付网关从单体迁移到微服务架构，QPS 从 3k 提升至 15k，P99 延迟从 800ms 降至 120ms。沉淀《支付系统微服务拆分指南》，后续 2 个业务线复用。",
        "设计分布式事务方案（Saga + 本地消息表），对账差异率从 0.3% 降至 0.01% 以下。"
      ]
    }
  ],
  "projectExperience": [
    {
      "name": "分布式任务调度平台",
      "url": "https://github.com/zhangsan/task-scheduler",
      "techStack": ["Go", "etcd", "gRPC", "Redis"],
      "description": "轻量级分布式任务调度系统，支持 Cron 表达式、任务依赖编排和故障自动转移。",
      "highlights": [
        "实现基于 etcd 的 Leader 选举与故障转移，调度可用性达 99.99%",
        "单节点支持 5000+ 任务并发执行，平均调度延迟 < 50ms"
      ]
    }
  ],
  "education": {
    "school": "某大学",
    "major": "计算机科学与技术",
    "degree": "本科",
    "startDate": "2018.09",
    "endDate": "2022.06"
  },
  "targetJD": "<可选的 JD 文本>"
}
```

## 字段定义

### basicInfo（必填）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 姓名 |
| phone | string | ✅ | 手机号 |
| email | string | ✅ | 邮箱 |
| github | string | 选填 | GitHub 主页 URL |
| blog | string | 选填 | 博客地址 |
| portfolio | string | 选填 | 作品集/个人网站 |
| yearsOfExperience | number | ✅ | 工作年限（数字或小数，如 0.5, 1, 3.5） |
| targetRole | string | ✅ | 求职目标（如"后端工程师""数据分析师""产品经理"等） |

### summary（选填）

- 类型：string
- 2-3 句话，包含角色 + 核心技能 + 量化亮点 + 求职方向
- 如未提供，Skill 会根据其他信息自动草拟

### techStack（必填）

按领域分组的对象，key 为分组名，value 为字符串数组。

**分组示例（按岗位领域）：**

| 岗位 | 建议分组 |
|------|---------|
| 后端 | 语言/框架、数据库/缓存、中间件/基础设施、测试/工具链 |
| 前端 | 语言/框架、状态管理、测试、工具链 |
| 数据分析 | 分析工具、数据库、可视化、机器学习 |
| DevOps | CI/CD、容器编排、监控/日志、IaaC 工具 |
| 产品经理 | 分析方法、原型工具、数据平台、协作工具 |

总计 12-20 项，分 3-5 组。每组按与目标岗位的匹配度排序，最强的放最前。

### workExperience（必填）

数组，每项为一个工作经历对象：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| company | string | ✅ | 公司名称 |
| role | string | ✅ | 职位名称 |
| startDate | string | ✅ | 开始日期，格式 YYYY.MM（如 2022.03） |
| endDate | string | 选填 | 结束日期，格式同上。至今则填 "至今" |
| background | string | 选填 | 项目/业务背景（SARL 的 S），1-2 句话 |
| responsibilities | string | 选填 | 角色与职责（SARL 的 T），1-2 句话 |
| highlights | string[] | ✅ | 主要成果，每条含动词 + 技术方案 + 量化成果。至少 1 条 |

### projectExperience（必填）

数组，每项为一个项目对象：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 项目名称 |
| url | string | 选填 | GitHub 仓库链接 |
| onlineUrl | string | 选填 | 在线预览/文档链接 |
| techStack | string[] | ✅ | 核心技术栈（3-5 项） |
| description | string | ✅ | 一句话项目简介 |
| highlights | string[] | ✅ | 亮点，每条含量化数据。至少 1 条 |

### education（必填）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| school | string | ✅ | 学校名称 |
| major | string | ✅ | 专业 |
| degree | string | ✅ | 学位（"本科""硕士""博士"） |
| startDate | string | 选填 | 入学时间，格式 YYYY（如 2018） |
| endDate | string | 选填 | 毕业时间，格式同上 |

### targetJD（选填）

- 类型：string
- 目标岗位的完整 JD 文本
- 如果提供，Skill 会在生成时进行关键词匹配和优先级调整

## YAML 示例

```yaml
basicInfo:
  name: 张三
  phone: "138-0000-0000"
  email: zhangsan@example.com
  github: https://github.com/zhangsan
  yearsOfExperience: 4
  targetRole: 数据分析师

techStack:
  分析工具:
    - Python
    - SQL
    - Excel
  数据库:
    - MySQL
    - ClickHouse
    - Redis
  可视化:
    - Tableau
    - Metabase
  其他:
    - A/B Testing
    - Airflow

workExperience:
  - company: 某电商平台
    role: 数据分析师
    startDate: "2022.03"
    endDate: "至今"
    highlights:
      - 构建用户分群模型使月留存率从 58% 提升至 70%

projectExperience:
  - name: 用户画像平台
    techStack:
      - Python
      - SQL
      - Tableau
    description: 基于行为数据的用户画像与分群系统
    highlights:
      - 搭建 RFM + K-Means 用户分群模型

education:
  school: 某大学
  major: 统计学
  degree: 本科
```
