# Resume 插件

> 简历相关技能集合 —— 从 Git 仓库提取项目经验、挖掘项目知识与技术难点、一键生成多岗位简历。

## 技能列表

| 技能 | 说明 | 触发方式 |
|------|------|---------|
| `extract-project` | 从 Git 仓库提取个人项目经验，生成符合 STAR/SARL 法则的简历文档 | 提供仓库地址 + "提取项目经验" |
| `extract-knowledge` | 从 Git 仓库挖掘核心业务场景、技术难点和关键设计，按技术/难点/业务场景维度输出结构化知识文档 | 提供仓库地址 + "提取知识" / "分析业务" / "挖掘技术" |
| `create-resume` | 交互式创建符合《简历规范》的完整简历（支持所有岗位），支持 JSON 文件导入和 JD 关键词匹配 | "创建简历" / "生成简历" / "写简历" |

## 安装

```bash
# 本地路径安装
/plugin install ./plugins/resume

# 或通过 Marketplace（发布后）
/plugin install resume@poseidon
```
