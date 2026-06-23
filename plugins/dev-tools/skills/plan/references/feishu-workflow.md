# 飞书文档存储工作流

> 此文档为 plan skill 的 L3 参考文档，当用户选择 `feishu` 作为文档存储方式时在对应 Step 中按需加载。
> 定义了飞书文档的本地优先（Local-First）同步模式。

---

## 一、核心原则

对飞书文档的所有操作遵循**本地优先、全量同步**模式：

```
本地编辑 → 全量推送至云端
云端拉取 → 全量覆盖本地
```

**为什么本地优先？**
- 飞书 CLI 不支持增量编辑（无法 patch 文档片段）
- 飞书文档的富文本格式（表格、图片）在 CLI 双向转换中可能丢失
- 本地 Markdown 文件便于版本控制、diff 对比和 agent 读写

---

## 二、文件命名与存储

### 2.1 本地临时目录

所有飞书文档的本地副本存储在 `.Poseidon/feishu/` 下：

```
.Poseidon/feishu/
├── <feature-slug>-clarification.md        # 需求澄清记录
├── <feature-slug>-requirement.md          # 需求文档
├── <feature-slug>-overall-plan.md         # 总体计划
├── <feature-slug>-detailed-plan-p1.md     # 详细计划 Phase 1
└── ...
```

### 2.2 飞书端对应关系

| 本地文件 | 飞书文档 | 文档 Token（用户提供） |
|----------|---------|----------------------|
| 各 plan 文档 | 一个飞书文件夹下的多个文档 | 用户提供文件夹或逐文档提供 token |

**首次使用飞书存储时**，向用户确认：
> 请提供飞书文档的存储位置：
> - 已有飞书文档 token（多个文档请逐一提供）
> - 飞书文件夹 token（将在该文件夹下自动创建文档）
> - 或提供一个父文档 token，我将在其下创建子文档

---

## 三、工作流

### 3.1 创建文档

当需要新建一个计划文档（如澄清记录、需求文档、计划文档）时：

```
Step A: 本地创建
  Write .Poseidon/feishu/<filename>.md
  ↓
Step B: 本地编辑完善
  在本地反复修改直到内容确定
  ↓
Step C: 全量推送至飞书
  使用飞书 CLI 创建飞书文档，内容为本地 Markdown 的完整内容
  ↓
Step D: 记录映射
  将飞书返回的文档 token 记录到 .Poseidon/feishu/doc-map.json
```

**飞书 CLI 命令（创建文档）：**
```bash
# 创建文档（根据飞书 CLI 实际接口调整）
feishu doc create --title "<文档标题>" --content "$(cat .Poseidon/feishu/<filename>.md)"
# 或先创建飞书文档再更新内容
feishu doc update <doc-token> --content "$(cat .Poseidon/feishu/<filename>.md)"
```

**如飞书 CLI 不支持直接 Markdown → 飞书文档转换**，先转换为 HTML：
```bash
# Markdown → HTML → 飞书文档
pandoc .Poseidon/feishu/<filename>.md -o .Poseidon/feishu/<filename>.html
feishu doc update <doc-token> --html "$(cat .Poseidon/feishu/<filename>.html)"
```

### 3.2 修改文档

当需要更新已有的飞书文档时：

```
Step A: 检查本地副本
  确认 .Poseidon/feishu/<filename>.md 存在且为最新版本
  ↓
Step B: 本地修改
  直接编辑本地 Markdown 文件（用 Edit/Write 工具）
  ↓
Step C: 全量推送至飞书
  将本地完整内容推送至云端，覆盖飞书文档
  ↓  (不使用增量更新——飞书 CLI 不支持)
Step D: 确认同步成功
  验证飞书 CLI 返回成功，记录同步时间
```

**飞书 CLI 命令（更新文档）：**
```bash
feishu doc update <doc-token> --content "$(cat .Poseidon/feishu/<filename>.md)"
```

**重要：** 始终以本地版本为准。如果本地和云端不一致，提示用户选择以哪边为准。

### 3.3 获取文档

当需要读取飞书上的文档时：

```
Step A: 从飞书全量拉取
  使用 feishu CLI 导出飞书文档内容
  ↓
Step B: 写入本地副本
  覆盖 .Poseidon/feishu/<filename>.md
  ↓
Step C: 读取本地副本
  Read .Poseidon/feishu/<filename>.md 获取内容
  ↓  (后续所有操作针对本地文件)
Step D: 更新映射表
  记录拉取时间到 doc-map.json
```

**飞书 CLI 命令（导出文档）：**
```bash
# 导出飞书文档为 Markdown
feishu doc export <doc-token> --format markdown --output .Poseidon/feishu/<filename>.md
# 或导出为纯文本再转换
feishu doc show <doc-token> > .Poseidon/feishu/<filename>.md
```

---

## 四、文档映射表

维护 `.Poseidon/feishu/doc-map.json` 记录本地文件与飞书文档的对应关系：

```json
{
  "feature": "<feature-slug>",
  "created": "<YYYY-MM-DD HH:MM>",
  "documents": {
    "clarification": {
      "local": ".Poseidon/feishu/<slug>-clarification.md",
      "feishu_token": "<doc-token>",
      "feishu_url": "<doc-url>",
      "last_sync": "<YYYY-MM-DD HH:MM>",
      "direction": "upload"
    },
    "requirement": {
      "local": ".Poseidon/feishu/<slug>-requirement.md",
      "feishu_token": "<doc-token>",
      "feishu_url": "<doc-url>",
      "last_sync": "<YYYY-MM-DD HH:MM>",
      "direction": "upload"
    },
    "overall-plan": {
      "local": ".Poseidon/feishu/<slug>-overall-plan.md",
      "feishu_token": "<doc-token>",
      "feishu_url": "<doc-url>",
      "last_sync": "<YYYY-MM-DD HH:MM>",
      "direction": "upload"
    },
    "detailed-plan-p1": {
      "local": ".Poseidon/feishu/<slug>-detailed-plan-p1.md",
      "feishu_token": "<doc-token>",
      "feishu_url": "<doc-url>",
      "last_sync": "<YYYY-MM-DD HH:MM>",
      "direction": "upload"
    }
  },
  "folder_token": "<folder-token or null>",
  "last_updated": "<YYYY-MM-DD HH:MM>"
}
```

**direction 字段说明：**
- `"upload"` — 最后操作是本地推送至云端（本地为准）
- `"download"` — 最后操作是云端拉取至本地（云端为准）

每个涉及飞书文档的操作后更新映射表。

---

## 五、飞书 CLI 可用性检查

每次使用飞书功能前，运行：

```bash
which feishu 2>/dev/null && feishu --version || echo "FEISHU_MISSING"
```

**CLI 不可用时：**
> 飞书 CLI 未安装或不可用。将降级为本地文件存储（`docs/requirements/`），所有文档将只保存在本地。你可以稍后安装飞书 CLI 后再手动同步。
>
> 飞书 CLI 安装指南：<根据实际情况提供>

**CLI 可用但未登录时：**
```bash
feishu auth status 2>&1
# 如果未登录
feishu auth login
```

---

## 六、异常处理

| 场景 | 处理方式 |
|------|---------|
| 飞书 CLI 推送失败（网络/权限） | 保留本地文件，告知用户错误信息，稍后重试 |
| 飞书文档已被其他人修改 | 拉取云端版本到临时文件 → 与本地 diff → 询问用户以哪边为准 |
| 飞书文档 token 失效/被删除 | 提示用户重新提供 token，或在飞书端重新创建 |
| Markdown → 飞书格式转换丢失 | 记录丢失的元素（表格/图片），建议用户在飞书端手动修正 |
| 本地副本丢失（如 `.Poseidon/` 被清理） | 从飞书重新拉取全量内容到本地 |

---

## 七、与 local 模式的对比

| 操作 | local 模式 | feishu 模式 |
|------|-----------|------------|
| 创建文档 | 直接 Write 到 `docs/requirements/` | 先 Write 到 `.Poseidon/feishu/`，再推送飞书 |
| 修改文档 | 直接 Edit 文件 | 先 Edit 本地副本，再全量推送飞书 |
| 读取文档 | 直接 Read 文件 | 如无本地副本则先拉取飞书，再 Read 本地 |
| 版本控制 | Git 管理 | 本地文件 Git 管理；飞书端自行维护历史 |
| 协作 | 查看本地文件 | 飞书端可多人协作；本地通过拉取同步 |

---

## 八、使用说明

此文档在以下场景被加载：
- **Step 0**：用户选择 `feishu` 存储方式 → 加载一、二、五章（初始化和检查）
- **Step 1.5 / Step 2 / Step 3 / Step 4**：生成文档并写入飞书 → 加载第三章对应节 + 第四章（映射表维护）
- **Step 6**：更新计划文档 → 加载三.2 节（修改文档流程）
- **任何需要读取已有飞书文档时** → 加载三.3 节（获取文档流程）
