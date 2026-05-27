# 软考备考插件 (ruankao)

软考系统分析师论文备考工具集，覆盖论文写作、优化、背诵辅助和音频生成四大场景。

## 技能列表

| 技能 | 触发方式 | 功能 |
|------|----------|------|
| `write-paper` | 提供论文题目要求写新论文 | 从零写作：解析题干 → 逐段生成 → 帮记词 → 字数校验 |
| `enhance-paper` | 要求优化/修改已有论文 | 论文诊断、字数合规检查、段落重写/扩展/压缩、PRD 一致性校验 |
| `teleprompter` | 要求生成/优化帮记词（记忆线） | 为论文段落生成标准格式背诵提示，统一全文提示风格 |
| `tts` | 要求将论文转为音频（mp3） | Markdown → 过滤正文 → 调用 edge-tts 免费合成 mp3 |

## 安装

### 方式一：从 GitHub 安装（推荐）

```bash
# 先添加 Poseidon 大仓为插件市场
/plugin marketplace add <your-github-user>/Poseidon

# 然后安装 ruankao 插件
/plugin install ruankao@poseidon-marketplace
```

### 方式二：直接 GitHub 仓库安装

如果 ruankao 作为独立仓库发布：

```bash
/plugin install https://github.com/HackNerd1/ruankao
```

### 方式三：本地路径安装

```bash
# 开发/测试 — 直接加载插件目录
claude --plugin-dir /path/to/Poseidon/plugins/ruankao

# 或在 Claude Code 会话中安装
/plugin install ./plugins/ruankao
```

### 方式四：手动安装技能

```bash
# 项目级（仅当前项目可用）
cp -r plugins/ruankao/skills/* .claude/skills/

# 全局（所有项目可用）
cp -r plugins/ruankao/skills/* ~/.claude/skills/
```

### 团队自动安装

在目标项目的 `.claude/settings.json` 中声明：

```json
{
  "plugins": {
    "marketplaces": ["<your-github-user>/Poseidon"],
    "install": ["ruankao"]
  }
}
```

团队成员 trust 项目后自动安装，无需手动操作。

## 目录结构

```
ruankao/
├── .claude-plugin/
│   └── plugin.json              # 插件清单
├── skills/
│   ├── write-paper/             # 论文从零写作
│   │   ├── SKILL.md
│   │   ├── references/          # 写作技巧、范文、PRD、ABSD、ServiceMesh
│   │   └── scripts/             # count_chars.py
│   ├── enhance-paper/           # 论文优化
│   │   ├── SKILL.md
│   │   ├── references/          # 写作技巧、范文、PRD
│   │   └── scripts/             # count_chars.py
│   ├── teleprompter/            # 帮记词生成
│   │   └── SKILL.md
│   └── tts/                     # 文本转语音
│       ├── SKILL.md
│       └── scripts/             # extract_body, tts_edge, tts_tencent
└── README.md
```

## 工作流协作

```
write-paper          enhance-paper       teleprompter        tts
(从零写作)           (优化打磨)          (背诵辅助)          (音频生成)
    │                    │                   │                  │
    ▼                    ▼                   ▼                  ▼
 生成初稿 ──────────→ 诊断优化 ──────────→ 统一记忆线 ──────→ 生成 mp3
    │                    │                   │                  │
    └─ count_chars ──────┴─ count_chars ─────┘                  │
                                                                 │
                                          extract_body ──────────┘
                                          tts_edge / tts_tencent
```

## 典型使用场景

1. **新题目练习**：用 `write-paper` 根据真题题干生成完整论文初稿
2. **精细打磨**：用 `enhance-paper` 诊断、修改、校验字数
3. **考前背诵**：用 `teleprompter` 统一记忆线格式，用 `tts` 生成音频通勤听
4. **全流程**：`write-paper` → `enhance-paper` → `teleprompter` → `tts`

## 验证

```bash
# 验证插件清单
claude plugin validate plugins/ruankao/.claude-plugin/plugin.json

# 本地加载测试
claude --plugin-dir plugins/ruankao
```
