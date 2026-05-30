---
name: extract-project
description: 从 Git 仓库提取个人项目经验，生成符合简历规范的 Markdown 文档。当用户提供 Git 仓库地址或本地路径，要求"提取项目经验"、"分析项目"、"生成简历项目"、"总结项目亮点"时触发。适用场景：简历更新、项目复盘、面试准备。
arguments: [<Git 仓库 URL 或本地路径>]
---

# 提取项目经验工作流

## 概述

从用户提供的 Git 仓库（远程 URL 或本地路径）中，分析仓库内容与提交历史，提取个人项目经验，按 STAR 法则生成符合简历规范的结构化 Markdown 文档。

输出文件命名：`${start_time}-${end_time}-${project_name}.md`，其中时间为用户在该项目的首次和最后提交日期。

## 工作流

### 第一步：解析输入

从用户提供的参数中判断：

1. **远程 URL**（含 `github.com` / `gitlab.com` / `gitee.com` 等）→ 进入第二步 Clone
2. **本地路径**（如 `/path/to/project` 或 `E:\project\xxx`）→ 直接使用，跳到第三步
3. **用户未提供** → 询问用户提供仓库地址

提取项目名称：
- URL：从路径末段提取，去掉 `.git` 后缀（如 `https://github.com/user/my-project.git` → `my-project`）
- 本地路径：使用目录名

向用户确认项目名称是否正确。

### 第二步：Clone 仓库

将远程仓库 clone 到 `.Poseidon/repo/<project_name>/`：

```bash
git clone <repo_url> ".Poseidon/repo/<project_name>/"
```

Clone 完成后，后续分析均基于该本地路径。

如果 `.Poseidon/repo/<project_name>/` 已存在，询问用户是否复用（跳过 clone）还是重新 clone。

### 第三步：确定分析时间范围

获取用户在该项目中的提交时间范围：

```bash
git log --author="<用户名>" --format="%ad" --date=short --reverse | head -1  # start_time
git log --author="<用户名>" --format="%ad" --date=short | head -1             # end_time
```

如果 `git log --author` 无法自动识别用户名（本地配置与仓库提交者不一致），按以下优先级确定作者：
1. 读取仓库根目录下的 `.git/config` 获取 `user.name`
2. 读取 `~/.gitconfig` 获取全局 `user.name`
3. 以上均失败 → 向用户询问 Git 用户名

如果用户的项目没有 git 历史（非 git 仓库），向用户询问项目时间范围，输出文件名中的时间使用当前日期作为 end_time。

### 第四步：并行派发子 Agent 分析

**同时派发三个子 Agent**，每个读取对应的 reference 作为 worker contract，分析结果写入 `.Poseidon/repo/<project_name>/` 下的中间文件：

| 子 Agent | Reference 文件 | 输出文件 | 职责 |
|---------|---------------|----------|------|
| Agent A | `references/tech-stack-detection.md` | `.Poseidon/repo/<project_name>/analysis/tech-stack.md` | 检测技术栈并分层 |
| Agent B | `references/repo-analysis.md` | `.Poseidon/repo/<project_name>/analysis/project-overview.md` | 项目概览与架构 |
| Agent C | `references/contribution-analysis.md` | `.Poseidon/repo/<project_name>/analysis/contributions.md` | 个人贡献与 STAR 亮点 |

派发方式：

```
Agent(description: "技术栈检测", prompt: "读取 references/tech-stack-detection.md 的完整契约，对 .Poseidon/repo/<project_name>/ 执行技术栈检测，结果写入 .Poseidon/repo/<project_name>/analysis/tech-stack.md")
Agent(description: "项目概览分析", prompt: "读取 references/repo-analysis.md 的完整契约，对 .Poseidon/repo/<project_name>/ 执行项目概览分析，结果写入 .Poseidon/repo/<project_name>/analysis/project-overview.md")
Agent(description: "贡献分析", prompt: "读取 references/contribution-analysis.md 的完整契约，对 .Poseidon/repo/<project_name>/ 分析用户 <用户名> 的贡献，结果写入 .Poseidon/repo/<project_name>/analysis/contributions.md")
```

创建输出目录后再派发：

```bash
mkdir -p ".Poseidon/repo/<project_name>/analysis"
```

**等待所有三个子 Agent 完成后**，进入第五步。

### 第五步：结果校验

逐个读取三个中间文件，检查质量：

**tech-stack.md 检查：**
- 是否覆盖了核心框架、构建工具、语言？
- 是否区分了主次（按使用量排序）？
- 是否遗漏了关键依赖？

**project-overview.md 检查：**
- 是否包含项目一句话描述？
- 是否覆盖了核心业务模块？
- 是否提取了项目亮点或创新点？

**contributions.md 检查：**
- 是否有至少 2-3 个 STAR 条目？
- 每个条目是否包含量化数据或具体成果？
- 是否遗漏了关键功能模块？

任一文件质量不达标 → 将其中的不足作为补充指令，重新派发子 Agent 补充分析。最多重试一次。

### 第六步：生成最终输出

读取三个中间文件，结合 `references/resume-output-template.md` 格式规范，生成最终 Markdown 文档。

生成要求：
1. 严格遵循模板的项目结构
2. 技术栈按使用程度分层（核心 → 辅助），限制 8 项以内
3. 核心贡献用 STAR 法则描述，至少含 1 个量化指标
4. 全文用第一人称"我"写作
5. 量化数据必须来自实际分析结果，不编造
6. 无法自动获取的信息（如在线链接、确切的性能数据）用 `<待补充>` 标记
7. **严禁在最终输出中出现 Git 统计数据**：提交次数、变更行数、提交历史表格、commit hash 等属于分析中间产物，不是简历内容。补充材料折叠区只允许放"完整依赖清单"和"架构说明"

保存路径：当前工作目录下的 `${start_time}-${end_time}-${project_name}.md`

将三个分析中间文件的内容整合，填充到模板中。仅将架构说明和完整依赖清单放入补充材料折叠区，其余中间分析结果一律不输出。

### 第七步：汇总报告

向用户报告：
- 输出文件路径
- 项目时间范围
- 检测到的技术栈
- 提取的 STAR 亮点数量
- 待补充的信息清单（带 `<待补充>` 标记的项）

## 关键规则

1. **并行优先**：第四步的三个子 Agent 必须同时派发，不允许串行
2. **中间文件落盘**：子 Agent 结果必须写入文件系统，不在上下文中口头传递
3. **只提取不编造**：所有数据必须来自仓库实际内容（代码、commit、README、配置文件），不确定的用 `<待补充>` 标记
4. **一份产出**：每次调用处理一个仓库，生成一份 Markdown
5. **语言跟随用户**：用户用中文提问就用中文输出，英文提问就用英文
6. **不修改仓库**：只读分析，不对仓库做任何写入操作（中间文件写入 `.Poseidon/repo/` 而非仓库内）
7. **量化提取要具体**：优先从 commit 消息、代码注释、README 中寻找数字（性能指标、数据量、用户数等）；没有则标 `<待补充>`
8. **Git 统计数据不出现在最终输出**：提交次数、变更行数、commit 列表等仅供分析过程使用，严禁写入最终 `.md` 文件。简历关注的是"做了什么、有什么影响"，不是"提交了多少次"

## 边界情况

- **非 Git 仓库**：没有提交历史 → 跳过 git log，向用户询问时间范围和技术栈
- **空仓库 / 仅 README**：只生成项目概览，技术栈和贡献部分标注为 `<待补充>`
- **大仓库 Clone 慢**：超过 2 分钟未完成 → 提示用户 Clone 可能较慢，询问是否改用本地路径
- **多 Git 用户**：仓库中有多个提交者 → 通过 git config 或询问用户确定分析目标
- **子目录项目**（Monorepo 中的子项目）：如果用户指定了子目录路径，只分析该子目录
- **私有仓库**：Clone 需要认证 → 提示用户配置 SSH key 或 Personal Access Token
