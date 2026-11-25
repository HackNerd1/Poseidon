# algo-coach

**算法学习插件 —— 把 LeetCode 刷题和 hello-algo.com 的系统学习关联起来，边刷边补知识点、边复盘解法。**

每道题从初始化到复盘形成闭环：`init-problem` 建题 → `link-knowledge` 补知识点与思路 → `optimize-solution` 复盘优化。

## 技能一览

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `init-problem` | 根据 LeetCode 链接拉取题目信息（标题、难度、描述、代码模板），在本地按题型归类创建文件，支持 10+ 编程语言 | 提供 LeetCode URL，或说“新建算法题”“初始化题目” |
| `link-knowledge` | 为算法题关联 hello-algo.com 知识点，并补充结构化解题思路（算法类别、适用依据、核心思路、解题步骤、复杂度分析） | 提供题目文件路径，或说“分析这道题”“关联知识点” |
| `optimize-solution` | 从代码质量和算法效率两个维度分析可优化点，生成优化版函数并标注改进原因，保留原函数不变 | 说“优化解法”“改进算法”“分析可优化点” |

## 安装

前置条件：Python 3 与 `git`；使用 Claude Code 或 Codex 插件流程时需已安装对应 CLI。

```bash
git clone https://github.com/HackNerd1/Poseidon.git
cd Poseidon
python3 scripts/install.py --platform claude --scope user --plugin algo-coach
```

把 `--platform` 换成 `codex` 或 `cursor` 可装到其他平台；`--scope repo` 安装到当前项目而非用户级目录。

## 使用

```text
/init-problem https://leetcode.cn/problems/two-sum/
/link-knowledge
/optimize-solution
```

典型顺序：先用 `init-problem` 生成题目文件，做题后让 `link-knowledge` 关联知识点并补思路，最后用 `optimize-solution` 对比优化版本。

## 许可证

[MIT License](../../LICENSE)，Copyright (c) 2026 HackNerd1。
