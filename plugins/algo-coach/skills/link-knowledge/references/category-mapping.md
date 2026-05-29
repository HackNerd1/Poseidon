# hello-algo 章节知识图谱

本文件列出 hello-algo.com 的完整章节结构，用于根据算法类别定位对应的知识页。

## 章节索引

### 第 4 章 · 数组与链表
- 章节首页: https://www.hello-algo.com/chapter_array_and_linkedlist/

### 第 5 章 · 栈与队列
- 章节首页: https://www.hello-algo.com/chapter_stack_and_queue/

### 第 6 章 · 哈希表
- 章节首页: https://www.hello-algo.com/chapter_hashing/

### 第 7 章 · 树
- 章节首页: https://www.hello-algo.com/chapter_tree/

### 第 8 章 · 堆
- 章节首页: https://www.hello-algo.com/chapter_heap/

### 第 9 章 · 图
- 章节首页: https://www.hello-algo.com/chapter_graph/

### 第 10 章 · 搜索
- 章节首页: https://www.hello-algo.com/chapter_searching/

### 第 11 章 · 排序
- 章节首页: https://www.hello-algo.com/chapter_sorting/

### 第 12 章 · 分治
- 章节首页: https://www.hello-algo.com/chapter_divide_and_conquer/

### 第 13 章 · 回溯
- 章节首页: https://www.hello-algo.com/chapter_backtracking/

### 第 14 章 · 动态规划
- 章节首页: https://www.hello-algo.com/chapter_dynamic_programming/

### 第 15 章 · 贪心
- 章节首页: https://www.hello-algo.com/chapter_greedy/
- 15.2 跳跃游戏: https://www.hello-algo.com/chapter_greedy/jump_game/
- 15.3 最大容量问题: https://www.hello-algo.com/chapter_greedy/max_capacity_problem/

## 算法类别 → 章节映射

| 算法类别 | hello-algo 章节 | 章节 URL |
|---------|----------------|----------|
| 贪心 (Greedy) | 第 15 章 | https://www.hello-algo.com/chapter_greedy/ |
| 动态规划 (DP) | 第 14 章 | https://www.hello-algo.com/chapter_dynamic_programming/ |
| 双指针 (Two Pointers) | 第 15 章 贪心 | https://www.hello-algo.com/chapter_greedy/ |
| 数组 (Array) | 第 4 章 | https://www.hello-algo.com/chapter_array_and_linkedlist/ |
| 哈希表 (Hash) | 第 6 章 | https://www.hello-algo.com/chapter_hashing/ |
| 二分查找 (Binary Search) | 第 10 章 | https://www.hello-algo.com/chapter_searching/ |
| 回溯 (Backtracking) | 第 13 章 | https://www.hello-algo.com/chapter_backtracking/ |
| 排序 (Sorting) | 第 11 章 | https://www.hello-algo.com/chapter_sorting/ |
| 栈/队列 (Stack/Queue) | 第 5 章 | https://www.hello-algo.com/chapter_stack_and_queue/ |
| 堆 (Heap) | 第 8 章 | https://www.hello-algo.com/chapter_heap/ |
| 分治 (Divide & Conquer) | 第 12 章 | https://www.hello-algo.com/chapter_divide_and_conquer/ |

## 查找策略

1. **精确搜索**：用题目标题关键词搜索 `site:hello-algo.com <关键词>`，通常能直接命中对应知识页
2. **备选搜索**：GitHub 搜索 `site:github.com/krahets/hello-algo <关键词>`
3. **近似匹配**：如果精确页未命中，自行判断题目属于哪个算法类别，在对应章节下找最接近的子页面（依据解题策略相似度、数据结构重合度、问题模式）

## 近似匹配指南

当题目在 hello-algo 没有独立专题页时，从以下维度判断最近知识点：

| 判断维度 | 说明 | 示例 |
|---------|------|------|
| 解题策略相似度 | 核心思路是否类似 | "接雨水"和"最大容量问题"都用双指针从两端收缩 |
| 数据结构重合度 | 是否使用相同的数据结构 | 单调栈问题可参考第 5 章栈与队列 |
| 问题模式 | 是否属于同类问题变种 | 区间问题、子序列问题、路径问题、背包问题变种 |

近似匹配结果示例：

| 常见题目 | 主类别 | 最近知识点 |
|---------|--------|-----------|
| 接雨水 (Trapping Rain Water) | 双指针 | §15.3 最大容量问题 + 第 4 章数组双指针技巧 |
| 最长回文子串 | 动态规划 / 双指针 | §14.X 子序列问题 + 第 4 章中心扩展 |
| 合并区间 | 排序 + 数组 | 第 11 章排序 + 第 4 章数组操作 |
| LRU 缓存 | 哈希表 + 链表 | 第 6 章哈希表 + 第 4 章链表 |
| 滑动窗口最大值 | 队列 / 堆 | 第 5 章队列 § 单调队列 + 第 8 章堆 |

### 跨章节关联

如果一道题涉及多个类别的技巧，可以同时引用多个章节的知识点：
- 先列出题目涉及的所有技巧
- 为每个技巧找到对应的 hello-algo 章节
- 在解题思路中说明各部分对应哪个知识点
- 标注主类别和辅助类别

## 站点信息

- 主页: https://www.hello-algo.com/
- GitHub 仓库: https://github.com/krahets/hello-algo
- URL 规律: `https://www.hello-algo.com/chapter_<英文章名>/<英文节名>/`
