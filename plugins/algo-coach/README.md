# 算法学习助手 (algo-coach)

将 LeetCode 刷题与系统学习关联起来：为每道题自动关联知识点、添加解题思路、分析并优化解法。

## 技能列表

| 技能 | 说明 |
|------|------|
| `init-problem` | 根据 LeetCode 链接自动拉取题目信息（标题、难度、描述、代码模板），在本地按题型归类创建文件，支持 10+ 编程语言 |
| `link-knowledge` | 为算法题关联 hello-algo.com 知识点并添加结构化解题思路（算法类别、适用依据、核心思路、解题步骤、复杂度分析） |
| `optimize-solution` | 从代码质量和算法效率两个维度分析可优化点，生成优化版函数并标注改进原因，保留原函数不变 |

## 安装

```bash
# 通过 Marketplace（推荐）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon
/plugin install algo-coach@poseidon

# 或本地路径安装
/plugin install ./plugins/algo-coach
```
