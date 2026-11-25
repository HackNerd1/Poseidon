# resume

**简历与面试插件 —— 从 Git 仓库提取项目经验，生成符合规范的简历，导出多种格式，并产出结构化面试准备材料。**

适用从“整理经历”到“面试前复习”的完整链路：`extract-project` / `extract-knowledge` 收集素材，`create-resume` 成稿，`convert-md` 导出，`prep-interview` 准备面试。

## 技能一览

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `extract-project` | 从 Git 仓库提取个人项目经验，生成符合 STAR/SARL 法则的简历文档 | 提供仓库地址，说“提取项目经验”“总结项目亮点” |
| `extract-knowledge` | 从 Git 仓库挖掘核心业务场景、技术难点和关键设计，按技术/难点/业务场景输出结构化知识文档 | 提供仓库地址，说“提取知识”“分析业务”“挖掘技术” |
| `create-resume` | 交互式创建符合《简历规范》的 Markdown 简历，支持 JSON/YAML 导入、对话式补充、JD 关键词匹配 | “创建简历”“生成简历”“更新简历” |
| `convert-md` | 用 Resumx 把 Markdown 简历转换为 PDF、HTML、DOCX、PNG，支持 30+ 内置风格 | “转换简历”“导出 PDF”“md 转 pdf” |
| `prep-interview` | 从简历提取技术栈与项目经验，生成按技术栈/项目/行为面试拆分的准备目录，并联网收集常考面试题；支持 JD 匹配 | “准备面试”“面试知识点”“JD 匹配” |

## 安装

前置条件：Python 3 与 `git`；使用 Claude Code 或 Codex 插件流程时需已安装对应 CLI。

```bash
git clone https://github.com/HackNerd1/Poseidon.git
cd Poseidon
python3 scripts/install.py --platform claude --scope user --plugin resume
```

把 `--platform` 换成 `codex` 或 `cursor` 可装到其他平台；`--scope repo` 安装到当前项目而非用户级目录。

## 使用

```text
/extract-project https://github.com/example/project
/create-resume
/convert-md
/prep-interview
```

常见链路：先提取项目经验与知识文档，再用 `create-resume` 成稿；需要投递时用 `convert-md` 导出 PDF，面试前用 `prep-interview` 生成复习目录。

## 环境要求

| 依赖 | 适用技能 | 说明 |
|------|----------|------|
| Python 3 + git | 全部 | 安装器与技能基础环境 |
| Node.js ≥ 18 + npm | `convert-md` | Resumx（`@resumx/resumx`）的运行环境，可用 `npx @resumx/resumx --version` 检查 |
| Claude Code / Codex / Cursor | 全部 | 通过 `scripts/install.py --platform` 选择 |

`convert-md` 依赖的 Resumx 未安装时，可用 `npm install -g @resumx/resumx` 安装，或直接用 `npx @resumx/resumx` 调用。

## 许可证

[MIT License](../../LICENSE)，Copyright (c) 2026 HackNerd1。
