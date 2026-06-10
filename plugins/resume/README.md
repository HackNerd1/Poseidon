# Resume 插件

> 简历与面试准备技能集合 —— 从 Git 仓库提取项目经验、挖掘项目知识与技术难点、一键生成多岗位简历、多格式导出、结构化面试准备。

## 技能列表

| 技能 | 说明 | 触发方式 |
|------|------|---------|
| `extract-project` | 从 Git 仓库提取个人项目经验，生成符合 STAR/SARL 法则的简历文档 | 提供仓库地址 + "提取项目经验" |
| `extract-knowledge` | 从 Git 仓库挖掘核心业务场景、技术难点和关键设计，按业务/技术/设计三维度输出结构化知识文档 | 提供仓库地址 + "提取知识" / "分析业务" / "挖掘技术" |
| `create-resume` | 交互式创建符合《简历规范》的完整简历，支持 JSON 导入和 JD 关键词匹配 | "创建简历" / "生成简历" / "写简历" |
| `convert-md` | 使用 Resumx 将 Markdown 简历转换为 PDF、HTML、DOCX、PNG 等格式，支持 30+ 内置风格 | "转换简历" / "导出 PDF" / "md 转 pdf" |
| `prep-interview` | 从 Markdown 简历提取技术栈与项目经验，生成结构化面试准备目录（按技术栈/项目/行为面试拆分多文件 + 联网收集常考面试题），支持 JD 匹配分析 | "准备面试" / "面试知识点" / "JD 匹配" |

## 安装

```bash
# 通过 Marketplace（推荐）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon
/plugin install resume@poseidon

# 或本地路径安装
/plugin install ./plugins/resume
```
