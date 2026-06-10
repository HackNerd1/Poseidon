# 软考备考插件 (ruankao)

软考系统分析师论文备考工具集，覆盖论文写作、优化、背诵辅助和音频生成四大场景。

## 技能列表

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `write-paper` | 从零写作完整论文：解析题干 → 逐段生成（摘要/背景/技术方法说明/论点展开/结尾）→ 帮记词 → 字数校验 | 提供论文题目要求写新论文 |
| `enhance-paper` | 论文诊断与优化：结构完整性检查、字数合规、段落重写/扩展/压缩、PRD 一致性校验、笔误修正 | 要求优化/修改已有论文 |
| `teleprompter` | 为论文段落生成标准格式背诵提示（记忆线），统一全文提示风格为 `> 记忆线：... -> ...` 格式 | 要求生成/优化帮记词 |
| `tts` | Markdown 论文转音频：自动过滤标题和引用行，调用 edge-tts 免费合成 mp3（微软神经语音） | 要求将论文转为音频 |

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
│       └── scripts/             # extract_body.py、tts_edge.py、tts_tencent.py
└── README.md
```
