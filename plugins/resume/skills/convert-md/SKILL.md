---
name: convert-md
description: 使用 Resumx 将 Markdown 简历转换为 PDF、HTML、DOCX、PNG 等多种格式。支持 30+ 内置风格选择，用户可指定输出格式和风格。当用户要求"转换简历"、"导出 PDF"、"md 转 pdf"、"生成简历 PDF"、"换个风格"时触发。
---

# Markdown 简历格式转换工作流

## 概述

使用 Resumx（`@resumx/resumx`）将 Markdown 简历转换为目标格式。Resumx 是一个面向 AI 工作流的开源简历渲染器，提供 30+ 内置风格、Tailwind CSS 排版、多格式输出（PDF / HTML / DOCX / PNG），适合与 `create-resume` 和 `extract-project` 技能的输出串联使用。

## 环境要求

- **Node.js** ≥ 18（Resumx 运行环境）
- **npm**（安装 Resumx）

## 工作流

### 第一步：环境检查与安装

检查 Resumx 是否可用：

```bash
npx @resumx/resumx --version
```

如果不可用，执行安装：

```bash
npm install -g @resumx/resumx
```

> 如果用户环境中没有 Node.js，先引导用户安装 Node.js（https://nodejs.org），然后重试。

安装完成后确认版本号并告知用户。

### 第二步：确定输入文件

判断输入来源：

1. **用户在调用时提供了文件路径** → 直接使用
2. **未提供文件路径** → 扫描当前工作目录下的 `.md` 文件：

```bash
ls *.md
```

如果有多个 `.md` 文件，列出让用户选择。如果只有一个，直接确认后使用。

3. **用户指定了目录** → 在该目录下按上述逻辑查找

确认文件存在后，读取文件开头几行向用户确认内容匹配：

```
找到简历文件：<文件名>（<行数> 行）
标题：<从文件第一行 H1 提取>
确认使用此文件进行转换？
```

### 第三步：选择输出格式

询问用户要输出哪些格式：

```
请选择输出格式（可多选）：

1. PDF    — 投递/打印首选，保留完整排版
2. HTML   — 网页展示，可部署到个人网站
3. DOCX   — Word 可编辑，方便招聘平台导入
4. PNG    — 图片预览，方便社交媒体分享

默认：PDF
```

对应的 Resumx 输出参数：

| 格式 | 参数 |
|------|------|
| PDF  | 默认输出格式（也支持 `--format pdf`） |
| HTML | `--format html` |
| DOCX | `--format docx` |
| PNG  | `--format png` |

用户可以多选，Resumx 一次命令可同时输出多种格式（逗号分隔：`--format pdf,html` 或重复传参：`-f html -f png`）。

### 第四步：选择风格

#### 4.1 获取可用风格列表

优先尝试获取 Resumx 当前支持的风格：

```bash
npx @resumx/resumx --help
```

如果动态获取失败，向用户展示以下精选风格分类供选择：

**经典专业型**（适合传统行业、国企、金融）
- `classic` — 经典衬线体排版，传统专业感
- `elegant` — 优雅简约，适合咨询/法律
- `academic` — 学术风格，适合科研/教育岗位

**现代简约型**（适合互联网、科技公司）
- `modern` — 现代无衬线体，干净利落（默认推荐）
- `minimal` — 极简风格，最大化内容密度
- `clean` — 清爽白底，适读性优先

**个性创意型**（适合设计、产品、创业公司）
- `creative` — 创意排版，视觉冲击力
- `bold` — 大胆配色，突出个性
- `vibrant` — 活力色调，年轻化风格

**紧凑高效型**（内容多、需要控制页数）
- `compact` — 紧凑排版，信息密度高
- `dense` — 极密布局，最小化空白
- `single-page` — 强约束单页，自动缩放适配

**暗色/特殊**
- `dark` — 深色主题，适合屏幕阅读
- `terminal` — 终端/黑客风格，适合极客岗位
- `newspaper` — 报刊栏式，适合文字密集型内容

> **注意**：上述风格名称为常见分类参考。实际可用风格以 `resumx --help` 输出为准。Resumx 内置 30+ 风格，各风格的适用性需在转换后通过预览确认。

#### 4.2 用户选择流程

```
请选择简历风格：

📌 推荐风格（适合中文技术简历）：
  • modern    — 现代简约，适合互联网岗位（默认）
  • classic   — 经典排版，适合传统行业
  • minimal   — 极简风格，信息密度高
  • compact   — 紧凑布局，内容多时推荐
  • vibrant   — 内置渐变色风格，彩色渐变背景 + 渐变标题（--css styles/vibrant.css）

如需查看更多风格，输入 "list" 查看完整列表。
输入风格名称即可，不选择将使用默认的 modern 风格。
```

如果用户输入了不在列表中的风格名，仍尝试传递给 Resumx（Resumx 可能有未列出的新风格）。

### 第五步：确认选项并执行转换

汇总用户选择，展示确认信息：

```
📋 转换确认

**输入文件**：resume.md
**输出格式**：PDF + HTML
**使用风格**：modern
**输出目录**：当前目录

确认开始转换？
```

用户确认后执行 Resumx 转换命令：

```bash
# 基础用法（输出 PDF）
npx @resumx/resumx <输入文件> -s <风格名>

# 多格式输出
npx @resumx/resumx <输入文件> -s <风格名> -f html -f png
# 或逗号分隔
npx @resumx/resumx <输入文件> -s <风格名> --format pdf,html
```

根据用户选择的格式组合，通过 `-f` / `--format` 传递。

#### Resumx 常用 CLI 参考

```bash
# 基础渲染
resumx resume.md                          # 默认输出 PDF
resumx resume.md -s modern                # 指定风格
resumx resume.md -w                       # 实时预览模式

# 多格式输出
resumx resume.md -f html                  # 额外输出 HTML
resumx resume.md -f docx                  # 额外输出 DOCX
resumx resume.md -f png                   # 额外输出 PNG
resumx resume.md -f pdf,html,docx         # 一次输出多种格式

# 输出路径
resumx resume.md -o ./out/resume          # 指定输出路径（不含扩展名）

# 使用自定义 CSS（内置 vibrant 风格）
resumx resume.md --css styles/vibrant.css
```

> 实际 CLI 接口以安装的 Resumx 版本为准。转换前先用 `npx @resumx/resumx --help` 确认当前版本的参数格式。

### 第六步：验证与报告

转换完成后：

1. **检查输出文件**：确认所有选中的格式文件都已生成
2. **检查文件大小**：PDF < 2MB 为佳，过大则提示可能影响邮件投递
3. **报告结果**：

```
✅ 转换完成！

**输出文件**：
  📄 resume.pdf   — 1.2 MB（风格：modern）
  🌐 resume.html  — 856 KB

**风格**：modern（现代简约型）

**文件位置**：<输出目录绝对路径>

**下一步建议**：
  - 在浏览器中打开 HTML 版检查排版
  - PDF 可直接用于邮件投递
  - 如对风格不满意，可重新运行并选择不同风格
  - 使用 `--watch` 参数可边改 Markdown 边实时预览
```

## 关键规则

1. **先查后装**：每次运行先检查 Resumx 是否已安装，避免重复安装
2. **动态发现风格**：优先用 `resumx --help` 确认当前版本支持的参数，风格名以实际 CLI 支持的为准
3. **默认值合理**：格式默认 PDF，风格默认 `modern`
4. **确认再执行**：汇总选项后必须经用户确认才运行转换命令
5. **不做内容修改**：仅负责格式转换，不修改 Markdown 内容。如发现内容问题（如待补充标记），提示用户但继续转换
6. **保留源文件**：转换不会修改原始 `.md` 文件
7. **语言跟随用户**：用户用中文提问就用中文回复
8. **技能换行规则**：Markdown 中单行换行不会产生实际断行。专业技能区每组写成独立一行时，行尾必须加两个空格（`  `）才能渲染为换行，否则所有分组会连成一段。转换前应检查输入文件是否遵循此规则，必要时自动修正
9. **内置风格**：本技能 `styles/` 目录下提供自维护的 CSS 样式，可通过 `--css` 参数使用（`--css <本目录>/styles/<名称>.css`），无需依赖 Resumx 内置风格

## 边界情况

- **Node.js 未安装**：引导用户安装 Node.js ≥ 18，提供下载链接，暂停流程
- **Markdown 文件不存在**：提示用户文件不存在，列出当前目录 `.md` 文件供选择
- **风格名无效**：Resumx 可能回退到默认风格，告知用户并建议用 `resumx --help` 查看有效参数
- **Markdown 包含中文**：Resumx 基于 Playwright，中文渲染依赖系统字体。如出现中文乱码，建议用户安装中文字体或使用已配置中文字体的风格
- **输出文件已存在**：Resumx 默认覆盖，确认前提示用户
- **转换失败**：检查错误信息，常见原因：Markdown 语法错误、风格不支持当前 Resumx 版本、Node.js 版本过低。针对性给出修复建议
- **文件内容包含 `<待补充>` 标记**：提示用户这些字段在输出中会显示为占位符，建议先完善内容再转换，但不阻止转换
