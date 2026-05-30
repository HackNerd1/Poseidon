---
name: repo-analysis
description: Worker contract — 分析仓库的项目概览、业务描述和架构特征。由 extract-project SKILL.md 派发的子 Agent 执行。
---

# 项目概览分析 Worker

## 输入

- 仓库本地路径：`<repo_path>`（由调用方传入）
- 输出路径：`<repo_path>/analysis/project-overview.md`（由调用方传入）

## 职责

从 README、项目结构和源码中提取项目的业务定位、核心模块和架构特征，为简历中的项目描述提供事实素材。

## 分析流程

### 1. 读取 README 和文档

按优先级读取：
1. `README.md` / `README_zh.md` / `README-zh.md`
2. `docs/` 目录下的主要文档
3. 根目录下的 `CONTRIBUTING.md`、`CHANGELOG.md`

从 README 中提取：
- 项目名称和一句话描述
- 项目解决什么问题（业务背景）
- 主要功能和特性列表
- 在线链接（GitHub Pages、Vercel、自定义域名等）
- 技术选型说明（如有）

### 2. 分析目录结构

列出项目的一级和二级目录，理解模块划分：

```bash
# 获取项目目录树（限制深度避免输出过长）
find <repo_path> -maxdepth 2 -type d ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/dist/*" ! -path "*/build/*" ! -path "*/target/*" | sort
```

识别项目类型和架构模式：
- **Monorepo**：存在 `packages/`、`apps/` 目录或多个 `package.json`
- **前后端分离**：存在 `client/` + `server/` 或 `frontend/` + `backend/`
- **单体应用**：单一 `src/` 目录
- **库/SDK**：存在 `lib/`、`src/` 且无入口 HTML
- **Electron 桌面应用**：存在 `electron/`、`main/` + `renderer/`
- **CLI 工具**：`package.json` 中有 `bin` 字段
- **移动端**：存在 `android/`、`ios/` 目录或 Flutter 结构

### 3. 读取入口文件和路由

从前端项目的路由配置或后端项目的 API 定义中，提取核心业务模块：

- **React Router**：读取路由配置文件（`routes.tsx`、`router.tsx`、`App.tsx` 中的 `<Route>`）
- **Next.js**：读取 `app/` 或 `pages/` 目录结构
- **Vue Router**：读取 `router/index.ts`
- **后端**：读取 controller / handler 文件列表

从路由/API 端点推断业务模块名称（如 `/trial-management` → 庭审管理模块）。

### 4. 提取项目亮点

检查以下信号判断项目是否包含高级实践：

| 信号 | 说明 |
|------|------|
| `Dockerfile` / `docker-compose.yml` | 容器化部署 |
| `.github/workflows/` | CI/CD 自动化 |
| `test/` 目录或 `*.test.*` / `*.spec.*` 文件 | 自动化测试 |
| `nginx.conf` / `traefik` 配置 | 反向代理/生产部署 |
| `electron-builder.yml` | 桌面应用打包分发 |
| `lerna.json` / `nx.json` / `turbo.json` | Monorepo 管理 |
| Storybook 配置 | 组件库/Design System |
| i18n / l10n 目录 | 国际化 |
| `worker/` 或 Web Worker 代码 | 性能优化（多线程） |
| `wasm` 文件或 Rust/WASM 依赖 | WebAssembly |
| 安全相关配置（CSP、helmet、OAuth） | 安全加固 |

### 5. 尝试获取在线信息（可选）

如果 README 中包含在线链接（GitHub Pages、Vercel、Netlify 等），使用 WebFetch 访问确认链接有效并记录。

## 输出格式

写入到 `<repo_path>/analysis/project-overview.md`：

```markdown
# 项目概览

## 基本信息
- **项目名称**：<项目名>
- **一句话描述**：<做什么的，解决什么问题>
- **在线链接**：<URL> 或 <待补充>
- **项目类型**：<Web 应用 / 桌面应用 / CLI / 库 / 移动端 / 全栈>

## 业务领域
- **行业/场景**：<如：司法/电商/教育/工具>
- **目标用户**：<如：法院书记员/个人开发者/企业>
- **核心功能**：
  1. <功能 1 — 使用业务术语>
  2. <功能 2>
  3. <功能 3>

## 架构概览
- **架构模式**：<前后端分离 / Monorepo / 单体 / 微服务>
- **工程结构**：<关键目录说明，不超过 5 项>
- **模块划分**：
  - <模块名> — <一句话说明做什么>

## 技术亮点
- <亮点 1>：<说明，如：Docker 多阶段构建 + GitHub Actions 自动发布>
- <亮点 2>
- <亮点 3>

## 简历可用素材
以下信息可直接用于简历项目描述：

- **项目角色**：<从 commit 活跃度和 README 推断，如：独立开发 / 核心开发者>
- **关键词**：<5-8 个可用于简历的关键词，如：Electron、React、WebSocket、SQLite、CI/CD>
- **是否有在线 Demo**：<是/否，URL>
```

## 关键规则

1. **业务优先**：项目描述用业务术语（"庭审笔录管理"），而非技术术语（"CRUD 操作"）
2. **覆盖核心模块**：至少列出 2-3 个核心业务模块
3. **不编造业务背景**：无法从 README/代码中获取的信息用 `<待补充>` 标记
4. **项目类型必须准确**："是什么"比"用什么"更重要
5. **亮点筛选**：只记录确实存在的高级实践，不把常规操作当亮点（如"使用了 Git"不是亮点）
