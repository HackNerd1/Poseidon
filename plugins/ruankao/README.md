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

```bash
# 通过 Marketplace（推荐）
/plugin marketplace add poseidon https://github.com/HackNerd1/Poseidon
/plugin install ruankao@poseidon

# 或本地路径安装
/plugin install ./plugins/ruankao
```

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

