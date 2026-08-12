# 飞书文档存储工作流

> 此文档为 `doc-sync` skill 的 L3 参考文档，当 provider 为 `feishu` 时按需加载。
>
> CLI：官方 [larksuite/cli](https://github.com/larksuite/cli)，可执行文件为 `lark-cli`。

---

## 一、核心原则

同步方向与写入粒度由用户指定；不明确时先询问，不要自行假定。

### 1.1 同步方向

| 模式 | 含义 | 典型操作 |
|------|------|---------|
| **本地优先** | 以本地 Markdown 为准，推送到飞书 | `create` / `update`（推送） |
| **远端优先** | 以飞书文档为准，拉取覆盖本地 | `pull` |

```
本地优先：本地编辑 → 推送至云端
远端优先：云端拉取 → 覆盖本地
```

### 1.2 写入粒度

`lark-cli docs +update` 支持全量覆盖与局部 patch，按场景选用：

| 粒度 | 命令 | 适用 |
|------|------|------|
| **全量覆盖** | `--command overwrite` | 本地整篇重写后同步；远端优先后重建本地再推回 |
| **局部 patch** | `--command str_replace` / `append` / `block_*` 等 | 用户只要改某一段；或远端已有富文本，不宜整篇 overwrite |

局部 patch 时仍可先改本地再推，或直接对远端文档下指令——以用户指定为准。不明确时询问：
> 本次要以本地为准还是飞书远端为准？整篇覆盖还是只改某一段？

### 1.3 其他注意

- 飞书富文本（表格、图片）在 Markdown 双向转换中可能丢失；`overwrite` 可能丢掉云端图片/评论
- 本地 Markdown 便于版本控制、diff 与 agent 读写；有协作冲突时先 diff 再问用户

---

## 二、文件命名与存储

### 2.1 本地临时目录

所有飞书文档的本地副本存储在 `.Poseidon/feishu/` 下。通用约定：`<slug>-<doc-type>.md`。下列为 **plan skill 常用文件名**（其他调用方可自定义 doc-type）：

```
.Poseidon/feishu/
├── <feature-slug>-clarification.md        # 需求澄清记录（plan）
├── <feature-slug>-requirement.md          # 需求文档（plan）
├── <feature-slug>-overall-plan.md         # 总体计划（plan）
├── <feature-slug>-detailed-plan-p1.md     # 详细计划 Phase 1（plan）
├── <feature-slug>-micro-plan.md           # Fast Path 简化计划（plan）
└── ...
```

### 2.2 飞书端对应关系

| 本地文件 | 飞书文档 | 文档 Token（用户提供） |
|----------|---------|----------------------|
| 各 plan 文档 | 一个飞书文件夹下的多个文档 | 用户提供文件夹或逐文档提供 token |

**首次使用飞书存储时**，向用户确认：
> 请提供飞书文档的存储位置：
> - 已有飞书文档 token / URL（多个文档请逐一提供）
> - 飞书文件夹 token（将用 `--parent-token` 在该文件夹下创建文档）
> - 或提供一个父文档 / wiki 节点 token，我将在其下创建子文档

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
Step C: 推送至飞书
  使用 lark-cli docs +create，内容为本地 Markdown
  ↓
Step D: 记录映射
  将返回的 document_id / url 记录到 .Poseidon/feishu/doc-map.json
```

**lark-cli 命令（创建文档）：**
```bash
# 创建 Markdown 云文档（--content 支持 @file）
lark-cli docs +create \
  --doc-format markdown \
  --title "<文档标题>" \
  --content @.Poseidon/feishu/<filename>.md

# 指定父文件夹 / wiki 节点
lark-cli docs +create \
  --doc-format markdown \
  --title "<文档标题>" \
  --parent-token "<folder-or-wiki-token>" \
  --content @.Poseidon/feishu/<filename>.md
```

成功时 stdout 为 JSON 信封（`ok: true`），从 `data.document.document_id` / `data.document.url` 取 token 与链接写入映射表。

### 3.2 修改文档

先确认同步方向与写入粒度（不明确则询问），再执行。

#### 本地优先 — 全量覆盖

```
Step A: 确认本地副本为最新意图版本
Step B: 编辑本地 Markdown
Step C: overwrite 推送到飞书
Step D: 验证 ok: true，更新映射（direction: upload）
```

```bash
lark-cli docs +update \
  --doc "<doc-token-or-url>" \
  --command overwrite \
  --doc-format markdown \
  --content @.Poseidon/feishu/<filename>.md
```

#### 本地优先 — 局部 patch

在本地定稿要改的片段后，对远端做精确更新（不必 overwrite 整篇）：

```bash
# 字符串替换
lark-cli docs +update \
  --doc "<doc-token-or-url>" \
  --command str_replace \
  --doc-format markdown \
  --pattern "<旧内容>" \
  --content "<新内容>"

# 文末追加
lark-cli docs +update \
  --doc "<doc-token-or-url>" \
  --command append \
  --doc-format markdown \
  --content @.Poseidon/feishu/<patch-fragment>.md
```

更细的 block 级操作见 `lark-cli skills read lark-doc references/lark-doc-update.md`。patch 成功后同步更新本地副本，使两侧一致。

#### 远端优先 — 先拉再改

用户要以飞书当前内容为准时：先走 3.3 拉取，再在本地编辑；若还需写回远端，再次确认粒度后推送。

**冲突：** 本地与云端不一致时，拉取云端到临时文件 → diff → 询问以哪边为准，禁止静默覆盖。

### 3.3 获取文档（远端优先）

当需要读取飞书上的文档，或以远端覆盖本地时：

```
Step A: 从飞书全量拉取
  使用 lark-cli docs +fetch 导出 Markdown
  ↓
Step B: 写入本地副本
  覆盖 .Poseidon/feishu/<filename>.md
  ↓
Step C: 读取本地副本
  Read .Poseidon/feishu/<filename>.md 获取内容
  ↓
Step D: 更新映射表
  记录拉取时间；direction: download
```

**lark-cli 命令（拉取文档）：**
```bash
lark-cli docs +fetch \
  --doc "<doc-token-or-url>" \
  --doc-format markdown \
  --jq '.data.document.content' \
  > .Poseidon/feishu/<filename>.md
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

## 五、lark-cli 可用性检查

每次使用飞书功能前，运行：

```bash
which lark-cli 2>/dev/null && lark-cli --version || echo "LARK_CLI_MISSING"
```

**CLI 不可用时：**
> `lark-cli` 未安装或不可用。将降级为本地文件存储（`docs/requirements/`），所有文档将只保存在本地。你可以稍后安装后再手动同步。
>
> 安装：`npx @larksuite/cli@latest install`  
> 仓库：[https://github.com/larksuite/cli](https://github.com/larksuite/cli)

**CLI 可用但未配置 / 未登录时：**
```bash
lark-cli auth status 2>&1
# 首次需配置应用凭证
lark-cli config init
# 登录（推荐常用 scopes）
lark-cli auth login --recommend
```

文档操作默认使用用户身份（`--as user`）。

---

## 六、异常处理

| 场景 | 处理方式 |
|------|---------|
| lark-cli 推送失败（网络/权限） | 保留本地文件，告知用户错误信息，稍后重试 |
| 飞书文档已被其他人修改 | 拉取云端版本到临时文件 → 与本地 diff → 询问用户以哪边为准 |
| 同步方向 / 写入粒度不明 | 询问：本地优先还是远端优先？整篇覆盖还是局部 patch？ |
| 飞书文档 token 失效/被删除 | 提示用户重新提供 token，或在飞书端重新创建 |
| Markdown → 飞书格式转换丢失 | 记录丢失的元素（表格/图片），建议用户在飞书端手动修正 |
| 本地副本丢失（如 `.Poseidon/` 被清理） | 从飞书重新拉取全量内容到本地 |
| 缺少 docs 相关 scope | 引导 `lark-cli auth login --recommend` 或按提示补齐 scope |

---

## 七、与 local 模式的对比

| 操作 | local 模式 | feishu 模式 |
|------|-----------|------------|
| 创建文档 | 直接 Write 到 `docs/requirements/` | 先 Write 到 `.Poseidon/feishu/`，再 `lark-cli docs +create` |
| 修改文档 | 直接 Edit 文件 | 按用户指定：本地优先推送（overwrite / patch）或远端优先先 pull |
| 读取文档 | 直接 Read 文件 | 远端优先时 `docs +fetch` 后 Read 本地；已有可信本地副本可直接 Read |
| 版本控制 | Git 管理 | 本地文件 Git 管理；飞书端自行维护历史 |
| 协作 | 查看本地文件 | 飞书端可多人协作；冲突时 diff 后询问 |

---

## 八、使用说明

此文档由 `doc-sync` skill 在 provider=`feishu` 时按需加载：
- **init / check** → 加载一、二、五章
- **create** → 加载三.1 + 第四章
- **update** → 加载一、三.2 + 第四章
- **pull** → 加载三.3 + 第四章
