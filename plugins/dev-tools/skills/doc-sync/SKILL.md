---
name: doc-sync
description: '本地 Markdown 与远端文档同步（飞书 / Notion）。当用户选择 feishu 或 notion 作为文档存储、需要创建/更新/拉取远端文档、维护 doc-map、或 plan skill 需要远端同步时触发。触发短语："同步飞书文档"、"同步 Notion"、"doc-sync"、"推送到飞书"、"ntn pages"。'
---

# Doc-Sync Skill — 本地优先的远端文档同步

## 概述

将本地 Markdown 与飞书 / Notion 文档双向同步。核心原则：**本地优先、显式目标、按 provider 加载细则**。

本 skill 可被 `plan` 等其他 skill 通过 `/doc-sync` 或 Skill tool 调用；也可由用户直接触发。

## 输入

1. **provider**（必需）：`feishu` 或 `notion`
2. **操作**（必需）：`init` | `create` | `update` | `pull` | `check`
3. **本地路径 / 文件名**（按操作需要）
4. **远端目标**（按 provider）：
   - `feishu`：文档 / 文件夹 token（可延后到首次推送时收集）
   - `notion`：**必须**由用户显式提供页面或 database 的 URL / ID

## 工作流

### Step 0：路由

| provider | 加载 reference |
|----------|----------------|
| `feishu` | Read `references/feishu.md` |
| `notion` | Read `references/notion.md` |

未识别 provider → 询问用户选择 `feishu` / `notion`，不要猜测。

### Step 1：可用性检查

按对应 reference 的「可用性检查」章节验证 CLI：

- `feishu` → `which feishu`；不可用则告知并建议降级 `local`
- `notion` → `which ntn`；不可用则告知并建议降级 `local`

### Step 2：按操作执行

| 操作 | 行为 |
|------|------|
| `init` | 初始化本地目录与 `doc-map.json`（`.Poseidon/feishu/` 或 `.Poseidon/notion/`） |
| `create` | 先写本地 Markdown，再推送远端，更新映射 |
| `update` | 编辑本地副本后全量覆盖远端，更新映射 |
| `pull` | 从远端拉取覆盖本地，再 Read 本地文件 |
| `check` | 只做 CLI / 登录状态检查，不写文档 |

细则（命令、映射表、异常处理）一律以已加载的 provider reference 为准，不在本文件重复。

### Step 3：回报

完成后报告：
1. provider + 操作
2. 本地路径
3. 远端标识（token / page_id / url，如有）
4. 映射表是否已更新
5. 失败时：是否建议降级 `local`

## 关键规则

1. **本地优先**：始终先写/改本地 Markdown，再同步远端
2. **Notion 显式目标**：未提供 URL / ID 时禁止猜测写入位置
3. **渐进加载**：只 Read 当前 provider 的 reference
4. **不负责计划内容**：不生成需求/计划正文；只负责存储与同步
5. **CLI 失败可降级**：保留本地文件，告知用户错误，建议改用 `local`

## 被其他 skill 调用时

调用方（如 `plan`）应：
1. 通过 `/doc-sync` 或 Skill tool 加载本 skill
2. 传入完整参数：`provider` + `操作` + `本地路径` +（`notion` 时）远端 URL / ID；禁止只写「同步」
3. 首次推送用 `create`，已有映射后用 `update`
4. 不要再读取 `plan/references/` 下已删除的 feishu/notion workflow 文件
