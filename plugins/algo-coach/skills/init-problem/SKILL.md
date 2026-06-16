---
name: init-problem
description: 根据 LeetCode 题目链接，在本地初始化算法题文件并归类到对应题型目录。当用户提供 LeetCode URL，或要求"新建算法题"、"初始化题目"、"创建题目文件"时触发。适用场景：开始刷一道新题前自动创建模板文件。
---

# 新建算法题工作流

## 概述

用户提供 LeetCode 题目链接，通过脚本自动拉取题目信息（标题、难度、描述、代码模板），在本地 `src/` 目录下按题型归类创建文件，生成带题目描述的注释块和空函数签名，方便直接开始实现。

## 工作流

### 第一步：解析用户输入

从用户消息中提取：

1. **LeetCode 题目 URL**（必需）：支持 `leetcode.com` 和 `leetcode.cn`
2. **目标语言**（用户未指定时必须询问）—— 如果用户消息中没说明语言，列出可选语言让用户选择，**不可跳过**
3. **目标根目录**（可选）：默认当前工作目录下的 `src/`

如果用户只给了题号（如"438"）或题目名（如"find-all-anagrams-in-a-string"）而非完整 URL，补全为标准 URL：

```
https://leetcode.com/problems/<slug>/
```

### 第二步：执行初始化脚本

调用内置脚本拉取题目信息并创建文件：

```bash
python <skill-dir>/scripts/init-problem.py "<leetcode-url>" [base-dir] [--lang=<lang>]
```

**脚本自动完成以下操作：**

1. 从 LeetCode GraphQL API 拉取题目元数据（无需登录）
2. 提取：标题、难度、题目描述（HTML → 纯文本）、标签、代码模板
3. 根据题目标签（topicTags）按优先级归类到对应题型目录：

| LeetCode 标签 | 归类目录 |
|---|---|
| sliding-window | SlidingWindow/ |
| dynamic-programming | DP/ |
| backtracking | Backtrack/ |
| greedy | Greedy/ |
| binary-search | BinarySearch/ |
| two-pointers | DoublePointer/ |
| array | Array/ |
| hash-table | Hash/ |
| depth-first-search | DFS/ |
| breadth-first-search | BFS/ |
| graph | Graph/ |
| tree / binary-tree | Tree/ |
| heap | Heap/ |
| stack | Stack/ |
| queue | Queue/ |
| linked-list | LinkedList/ |
| sorting | Sorting/ |
| divide-and-conquer | DivideAndConquer/ |
| bit-manipulation | BitManipulation/ |
| union-find | UnionFind/ |
| trie | Trie/ |
| design | Design/ |
| math | Math/ |
| string | String/ |
| (无匹配) | General/ |

**优先级规则**：算法技巧（滑动窗口、DP、回溯等）优先于数据结构（数组、哈希表、链表等）。例如一道题标签为 `["hash-table", "string", "sliding-window"]`，会归类到 `SlidingWindow/` 而非 `Hash/`。

4. 若目录不存在，自动创建
5. 生成文件，命名格式：`(难度)题目slug.扩展名`

### 第三步：检查生成结果

脚本执行成功后，向用户展示：

- 题目标题与编号
- 难度
- 归类目录（以及命中的标签）
- 生成的文件路径
- 代码模板语言

如果文件已存在（之前初始化过），脚本会报错退出，此时向用户确认是否覆盖。

### 第四步：后续引导

文件创建后，向用户说明可以进行的下一步操作：

- 直接打开文件开始实现算法
- 使用 `/algo-coach:link-knowledge` 为题目添加知识点关联
- 实现完成后使用 `/algo-coach:optimize-solution` 分析可优化点

---

## 关键规则

1. **不重复创建**：如果目标文件已存在，脚本会报错。先询问用户是否覆盖，不要直接删除
2. **题目内容以 LeetCode 为准**：描述从 API 拉取，不手动编造
3. **描述语言跟随题目源**：`leetcode.com` 返回英文描述，`leetcode.cn` 返回中文描述
4. **目录名写入时检查**：创建目录前脚本自动检查是否存在，已存在则复用
5. **语言跟随用户**：用户用什么语言交流就用什么语言回复
6. **文件命名中的难度**：使用英文小写 `easy` / `medium` / `hard`
7. **语言未指定必须先问**：如果用户只给了题目 URL 没给语言，必须先列出支持的语言让用户选择，确认后再执行脚本。不可自作主张给定默认语言

---

## 支持的语言

| 语言 | --lang 参数 |
|------|-----------|
| TypeScript | `typescript` |
| JavaScript | `javascript` |
| Python3 | `python3` |
| Java | `java` |
| C++ | `cpp` |
| C | `c` |
| C# | `csharp` |
| Go | `go` |
| Rust | `rust` |
| Kotlin | `kotlin` |
| Swift | `swift` |
