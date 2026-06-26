# Notion 文档存储工作流

> 此文档为 plan skill 的 L3 参考文档，当用户选择 `notion` 作为文档存储方式时按需加载。
> 仅覆盖 Notion 文档内容的创建、更新、读取；不负责模板探测、项目模板复刻或数据库结构管理。

---

## 一、核心原则

对 Notion 文档的操作遵循**显式目标、本地优先、内容同步**模式：

```
用户提供 Notion URL / ID
→ 本地 Markdown 编辑
→ 创建或更新目标页面内容
→ 必要时回读到本地
```

核心约束：
- **必须由用户显式提供目标 URL 或 ID**
- 未提供时，不要猜测父页面、database、模板或归档位置
- 本地 Markdown 始终是事实源
- 仅保证页面内容创建与更新，不承诺复刻 UI 模板行为

---

## 二、输入要求

### 2.1 用户必须提供的标识

Notion 模式下，用户必须显式提供以下之一：
- 页面 URL
- 页面 ID
- database URL
- database ID

如果用户未提供，必须提示：

> 请提供 Notion 页面或 database 的 URL / ID。未提供目标标识时，我不会自动猜测写入位置。

### 2.2 本地目录

所有 Notion 文档的本地副本存储在 `.Poseidon/notion/` 下：

```
.Poseidon/notion/
├── <feature-slug>-clarification.md
├── <feature-slug>-requirement.md
├── <feature-slug>-overall-plan.md
├── <feature-slug>-detailed-plan-p1.md
└── doc-map.json
```

---

## 三、标准命令

先固定 API 版本：

```bash
export NOTION_API_VERSION=2026-03-11
```

### 3.1 在父页面下创建文档页

```bash
ntn pages create \
  --parent page:<parent-page-id> \
  --content "$(cat .Poseidon/notion/<filename>.md)"
```

适用场景：
- 用户提供的是页面 URL / 页面 ID
- 需要在该页面下创建新的计划文档页

### 3.2 在 database 下创建页面

```bash
ntn api v1/pages --method POST --data '{
  "parent": { "database_id": "<database-id>" },
  "properties": {
    "title": {
      "title": [
        { "text": { "content": "<page-title>" } }
      ]
    }
  },
  "markdown": "'"$(cat .Poseidon/notion/<filename>.md | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' )"'"
}'
```

适用场景：
- 用户提供的是 database URL / database ID
- 只要求创建一个有正文内容的页面

注意：
- database 的标题字段不一定叫 `title`，如果当前库标题属性名称不同，先用 `ntn api v1/databases/<database-id>` 或现有上下文确认字段名
- 若字段名未知且高风险，先让用户提供目标字段名或改用父页面模式

### 3.3 更新已有页面内容

```bash
ntn pages edit <page-id> --content "$(cat .Poseidon/notion/<filename>.md)"
```

适用场景：
- 用户明确提供了已有页面 ID / URL
- 需要覆盖其正文内容

### 3.4 读取页面内容到本地

```bash
ntn pages get <page-id> > .Poseidon/notion/<filename>.md
```

适用场景：
- 需要把已有页面内容拉回本地继续编辑

---

## 四、推荐流程

### 4.1 创建文档

当用户要新建 Notion 文档时：

```
Step A: 校验用户是否提供 URL / ID
  未提供 → 提示用户补充
  ↓
Step B: 在本地写 Markdown
  Write .Poseidon/notion/<filename>.md
  ↓
Step C: 根据目标类型选择命令
  page → 用 3.1
  database → 用 3.2
  ↓
Step D: 记录映射
  更新 doc-map.json
```

### 4.2 更新文档

当用户要更新已有 Notion 文档时：

```
Step A: 校验用户是否提供 page URL / ID
  未提供 → 提示用户补充
  ↓
Step B: 编辑本地 Markdown
  Edit .Poseidon/notion/<filename>.md
  ↓
Step C: 用 3.3 覆盖更新页面正文
  ↓
Step D: 必要时用 3.4 回读校验
```

### 4.3 读取文档

当用户要读取已有 Notion 文档时：

```
Step A: 校验用户是否提供 page URL / ID
  未提供 → 提示用户补充
  ↓
Step B: 用 3.4 拉取页面 Markdown
  ↓
Step C: 后续所有修改先针对本地文件
```

---

## 五、文档映射表

维护 `.Poseidon/notion/doc-map.json`：

```json
{
  "feature": "<feature-slug>",
  "created": "<YYYY-MM-DD HH:MM>",
  "documents": {
    "clarification": {
      "local": ".Poseidon/notion/<slug>-clarification.md",
      "page_id": "<page-id>",
      "page_url": "<notion-url>",
      "target_type": "page",
      "last_sync": "<YYYY-MM-DD HH:MM>",
      "direction": "upload"
    }
  },
  "target_id": "<page-id or database-id>",
  "target_type": "page or database",
  "last_updated": "<YYYY-MM-DD HH:MM>"
}
```

`direction` 说明：
- `upload`：本地推送到 Notion
- `download`：从 Notion 拉回本地

---

## 六、可用性检查

每次使用 Notion 功能前，运行：

```bash
which ntn 2>/dev/null && ntn --version || echo "NTN_MISSING"
```

CLI 可用但未登录时：

```bash
ntn doctor
ntn login
```

---

## 七、异常处理

| 场景 | 处理方式 |
|------|---------|
| 用户未提供 URL / ID | 直接提示用户补充，不自动猜测 |
| `ntn` 不可用或未登录 | 降级为本地文件存储 |
| page_id / database_id 无效 | 提示用户重新提供正确标识 |
| database 标题字段名不明确 | 先确认字段名，再创建；不盲写 |
| 页面已被他人改写 | 先拉取回本地 diff，再决定覆盖 |
| 页面内容更新失败 | 保留本地 Markdown，提示稍后重试 |

---

## 八、使用说明

此文档在以下场景被加载：
- **Step 0**：用户选择 `notion` 存储方式 → 加载一、二、六章
- **创建 Notion 文档时** → 加载三.1 / 三.2 / 四.1 / 五章
- **更新已有 Notion 页面时** → 加载三.3 / 四.2 / 五章
- **读取已有 Notion 页面时** → 加载三.4 / 四.3 / 五章
