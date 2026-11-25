# ruankao

**软考备考插件 —— 面向系统分析师论文写作：从题干成稿、诊断优化、帮记词生成到 TTS 音频，覆盖完整备考闭环。**

四个技能对应四个场景：写新论文、改已有论文、背记忆线、听论文，产物都是本地 Markdown 或 mp3。

## 技能一览

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `write-paper` | 从零写作完整论文：解析题干 → 逐段生成（摘要/背景/技术方法说明/论点展开/结尾）→ 帮记词 → 字数校验 | 提供论文题目要求写新论文 |
| `enhance-paper` | 论文诊断与优化：结构完整性检查、字数合规、段落重写/扩展/压缩、PRD 一致性校验、笔误修正 | 要求优化或修改已有论文 |
| `teleprompter` | 为论文段落生成标准格式背诵提示（记忆线），统一全文为 `> 记忆线：... -> ...` 格式 | 要求生成或优化帮记词 |
| `tts` | Markdown 论文转音频：自动过滤标题和引用行，用 edge-tts 免费合成 mp3（微软神经语音），备选腾讯云 TTS | 要求把论文转为音频 |

## 安装

前置条件：Python 3 与 `git`；使用 Claude Code 或 Codex 插件流程时需已安装对应 CLI。

```bash
git clone https://github.com/HackNerd1/Poseidon.git
cd Poseidon
python3 scripts/install.py --platform claude --scope user --plugin ruankao
```

把 `--platform` 换成 `codex` 或 `cursor` 可装到其他平台；`--scope repo` 安装到当前项目而非用户级目录。

## 使用

```text
/write-paper
/enhance-paper
/teleprompter
/tts
```

典型顺序：`write-paper` 成稿后，用 `enhance-paper` 做结构与字数体检，再用 `teleprompter` 生成记忆线，最后用 `tts` 导出音频通勤时听。

## 环境要求

| 依赖 | 适用技能 | 说明 |
|------|----------|------|
| Python 3 | 全部 | 安装器与脚本环境 |
| `edge-tts` | `tts` | 默认方案，免费无需密钥，安装命令 `pip install edge-tts` |
| 平台 CLI | 全部 | Claude Code / Codex / Cursor，通过 `scripts/install.py --platform` 选择 |

`tts` 需要联网调用微软语音服务；腾讯云 TTS 为备选方案，需要自备账号与密钥。

## 目录结构

```text
ruankao/
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

## 许可证

[MIT License](../../LICENSE)，Copyright (c) 2026 HackNerd1。
