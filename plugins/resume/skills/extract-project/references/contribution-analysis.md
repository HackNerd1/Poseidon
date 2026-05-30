---
name: contribution-analysis
description: Worker contract — 分析用户在仓库中的个人贡献，提取 STAR 法则描述的亮点。由 extract-project SKILL.md 派发的子 Agent 执行。
---

# 个人贡献分析 Worker

## 输入

- 仓库本地路径：`<repo_path>`（由调用方传入）
- Git 用户名：`<author_name>`（由调用方传入，从 `.git/config` 或用户提供获取）
- 输出路径：`<repo_path>/analysis/contributions.md`（由调用方传入）

## 职责

分析用户在仓库中的提交历史，提取技术贡献并按 STAR 法则组织成简历可用的描述条目。

## 分析流程

### 1. 获取用户提交统计

```bash
# 用户提交总数
git -C <repo_path> log --author="<author_name>" --oneline | wc -l

# 用户提交时间范围
git -C <repo_path> log --author="<author_name>" --format="%ad" --date=short --reverse | head -1
git -C <repo_path> log --author="<author_name>" --format="%ad" --date=short | head -1

# 用户变更量统计
git -C <repo_path> log --author="<author_name>" --shortstat | grep -E "fil(e|es) changed" | awk '{files+=$1; inserted+=$4; deleted+=$6} END {print "files:", files, "insertions:", inserted, "deletions:", deleted}'

# 用户在总提交中的占比
git -C <repo_path> shortlog -sn --all | head -20
```

### 2. 提取关键提交

筛选有意义的提交（排除 chore、fix typo 等琐碎提交）：

```bash
# 获取用户的所有提交信息（含文件变更）
git -C <repo_path> log --author="<author_name>" --format="%h %s" --name-only
```

从提交消息中识别：
- **功能开发**：含 `feat`、`add`、`实现`、`新增`、`开发`、`feature`、`support` 关键词
- **重构优化**：含 `refactor`、`perf`、`optimize`、`重构`、`优化`、`improve`、`性能` 关键词
- **问题修复**：含 `fix`、`bug`、`修复`、`解决`、`resolve` 关键词
- **架构变更**：含 `arch`、`migrate`、`upgrade`、`迁移`、`升级` 关键词

按功能模块分组提交（同目录或同类文件的提交归为一组）。

### 3. 识别核心贡献点

将分组的提交映射为 2-5 个核心贡献点。每个贡献点应具备：

- **做了什么**（Action）：具体实现了什么功能/模块
- **为什么这样做**（Context）：解决了什么问题或痛点
- **有什么结果**（Result）：寻找量化数据

### 4. 提取量化数据

从以下来源主动寻找数字：

**提交消息中：**
- 性能数字（"首屏从 3s 降到 1.2s"、"QPS 从 1k 提到 3k"）
- 规模数字（"支持 10 万条数据"）
- 百分比（"体积减少 40%"、"覆盖率 85%"）

**README 中：**
- Lighthouse 评分、性能指标
- 用户数、下载量、Star 数（如有徽章）

**代码注释中：**
- 性能相关注释（"批量处理 5000 条"、"缓存过期时间 5min"）

**测试文件中：**
- 测试用例数量作为"测试覆盖率"参考
- Benchmark 数据

### 5. 按 STAR 法则组织

每个核心贡献点按以下模板描述：

```markdown
### <贡献标题>

- **S** (背景): <项目背景与挑战 — 一句话>
- **T** (目标): <你的角色与目标 — 一句话>
- **A** (动作): <具体技术方案 — 2-3 句话>
- **R** (结果): <量化成果 — 一句话，没有则标 <待补充>>
```

## 输出格式

写入到 `<repo_path>/analysis/contributions.md`：

```markdown
# 个人贡献分析

## 用户信息
- **Git 用户名**：<author_name>
- **提交数量**：<N> 次
- **时间范围**：<start_date> ~ <end_date>
- **总变更量**：<insertions> 行新增 / <deletions> 行删除

## 核心贡献点

### <贡献标题 1>

- **S** (背景): <...>
- **T** (目标): <...>
- **A** (动作): <...>
- **R** (结果): <...>

### <贡献标题 2>
（同上）

## 量化数据清单
列出所有找到的数字，标注来源：

| 指标 | 数值 | 来源 |
|------|------|------|
| <指标名> | <数值> | <commit hash / README / 代码注释> |

## 简历 STAR 条目（可直接使用）

按简历规范润色后的 STAR 描述条目：

1. **<一句话 STAR>**
   技术栈：<涉及的技术>

2. **<一句话 STAR>**
   技术栈：<涉及的技术>

格式示例：
1. **主导 React 18 + TypeScript 电商平台重构，首屏从 3.2s 降至 1.8s (Lighthouse 65→92)，转化率提升 15%**
   技术栈：React 18、TypeScript、Next.js、Vercel
```

## 关键规则

1. **不编造数字**：量化数据必须来自仓库实际内容，找不到的用 `<待补充>` 标记
2. **突出个人贡献**：聚焦于"我做了什么"，而非"项目有什么"
3. **提交分组**：同一功能模块的多次提交合并为一个贡献点
4. **区分重要度**：核心贡献点按技术深度和业务影响排序，最重要的放前面
5. **最少 2 个贡献点**：即使提交较少，也要找出至少 2 个有价值的贡献角度
6. **如果用户提交数极少**（< 10 次或占比 < 10%）：标注"贡献占比较低，以下分析基于有限提交"，但依然尽力提取
