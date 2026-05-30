---
name: tech-stack-detection
description: Worker contract — 检测仓库的技术栈并按使用程度分类。由 extract-project SKILL.md 派发的子 Agent 执行。
---

# 技术栈检测 Worker

## 输入

- 仓库本地路径：`<repo_path>`（由调用方传入）
- 输出路径：`<repo_path>/analysis/tech-stack.md`（由调用方传入）

## 职责

分析仓库中的所有技术依赖和源码，输出分类后的技术栈清单。

## 分析流程

### 1. 读取依赖声明文件

按优先级检查以下文件（存在即解析）：

| 文件 | 提取内容 |
|------|---------|
| `package.json` | `dependencies` + `devDependencies`，重点关注框架、构建工具、状态管理、测试框架 |
| `tsconfig.json` / `jsconfig.json` | TypeScript 配置、路径别名、target 版本 |
| `Cargo.toml` / `go.mod` / `requirements.txt` / `Pipfile` / `pyproject.toml` | 对应语言的核心依赖 |
| `pom.xml` / `build.gradle` | Java/Kotlin 项目的依赖 |
| `Gemfile` | Ruby 项目的依赖 |
| `CMakeLists.txt` | C/C++ 构建配置 |
| `vite.config.*` / `webpack.config.*` / `rollup.config.*` | 构建工具和插件 |
| `.eslintrc.*` / `.prettierrc.*` | 代码规范工具 |
| `docker-compose.yml` / `Dockerfile` | 容器化和基础设施 |

### 2. 分析源码文件

通过文件扩展名统计确定实际使用的语言和框架：

```bash
# 统计源码文件类型（排除 node_modules、dist、build、.git）
find <repo_path> -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.vue" -o -name "*.py" -o -name "*.rs" -o -name "*.go" -o -name "*.java" -o -name "*.kt" -o -name "*.rb" -o -name "*.cpp" -o -name "*.c" -o -name "*.css" -o -name "*.scss" -o -name "*.less" \) ! -path "*/node_modules/*" ! -path "*/dist/*" ! -path "*/build/*" ! -path "*/.git/*" | sed 's/.*\.//' | sort | uniq -c | sort -rn
```

### 3. 识别框架与库

从依赖中识别主流框架和库，按类别归类：

| 类别 | 识别关键词 |
|------|-----------|
| 前端框架 | react, vue, angular, svelte, next, nuxt, gatsby |
| 桌面框架 | electron, tauri, nw.js |
| 移动框架 | react-native, flutter, ionic |
| 后端框架 | express, koa, fastapi, django, flask, spring, gin, actix |
| 状态管理 | redux, zustand, mobx, pinia, vuex, recoil, jotai |
| UI 库 | ant-design, element-ui, material-ui, tailwindcss, shadcn |
| 构建工具 | vite, webpack, turbopack, esbuild, rollup, parcel |
| 测试 | jest, vitest, cypress, playwright, testing-library, mocha |
| 数据库 | prisma, typeorm, sequelize, mongoose, drizzle, kysely |
| CI/CD | github actions, gitlab ci, jenkins, docker |
| 云服务 | aws, azure, gcp, vercel, cloudflare, fly.io |

### 4. 读取项目配置获取更多信息

从 `package.json` 的 `scripts` 字段获取常用命令，判断使用的工具：
- `"dev": "vite"` → Vite
- `"dev": "next dev"` → Next.js
- `"build": "webpack"` → Webpack
- `"lint": "eslint"` → ESLint
- `"test": "vitest"` → Vitest

## 输出格式

写入到 `<repo_path>/analysis/tech-stack.md`：

```markdown
# 技术栈分析结果

## 语言
- <主要语言>（占比最高）
- <次要语言>（如有）

## 框架与运行时
| 名称 | 类别 | 判断依据 |
|------|------|---------|
| React 18 | 前端框架 | package.json dependencies + .tsx 文件 |
| Electron 28 | 桌面框架 | package.json dependencies + electron-builder.yml |

## 构建与工具链
| 名称 | 用途 | 判断依据 |
|------|------|---------|
| Vite 5 | 构建工具 | vite.config.ts |
| TypeScript 5 | 类型系统 | tsconfig.json |

## 状态管理与数据层
（同上表格格式）

## 测试
（同上表格格式）

## 基础设施
（同上表格格式）

## 技术栈汇总（供简历使用）

按使用程度分两层：

**核心：** <列出 3-5 项最核心的技术，按重要性排序>
**辅助：** <列出 2-4 项辅助技术>

格式示例：
核心：React 18、TypeScript、Electron、Vite
辅助：Zustand、Tailwind CSS、Vitest、Docker
```

## 关键规则

1. **统计驱动**：技术占比判断依据文件数量统计 + 依赖声明，不可凭印象猜测
2. **区分核心与辅助**：核心 = 项目离开它无法运行（框架、运行时、核心语言）；辅助 = 开发工具、测试、样式
3. **版本号**：优先从 lock 文件或 package.json 中提取精确版本号，没有则只写名称
4. **不遗漏关键工具**：检查 `scripts` 字段确保不遗漏构建/测试工具
5. **如果仓库几乎为空**（无依赖文件、仅有少量源码）：输出"技术栈检测受限"，仅列出可识别的语言
