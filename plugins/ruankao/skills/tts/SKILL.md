---
name: tts
description: 论文文本转语音（TTS）。当用户要求将论文 Markdown 文档转为音频（mp3）时触发。默认使用免费 edge-tts 方案（微软神经语音），备选腾讯云 TTS。
arguments: [<论文路径>]
---

# 论文文本转语音（TTS）工作流

## 方案选择

| 方案 | 费用 | 需要密钥 | 音质 |
|------|------|----------|------|
| **edge-tts（推荐）** | 免费 | 否 | 微软神经语音，Azure 同款 |
| 腾讯云 TTS | 按字符计费 | 是 | 普通 |

优先用 edge-tts，零门槛、零费用、音质好。

## 工作流（edge-tts）

### 第一步：安装依赖

```bash
pip install edge-tts
```

### 第二步：提取正文

脚本自动过滤 Markdown 中的标题和引用行，只保留正文朗读：

| 行类型 | 正则 | 处理 |
|--------|------|------|
| 标题行 | `^\s*#` | 跳过 |
| 引用/记忆线 | `^\s*>` | 跳过 |
| 空行 | `^\s*$` | 跳过 |
| 普通段落 | 其余 | 合并为正文 |

可独立执行提取工具预览：

```bash
python scripts/extract_body.py "src/计算与储存分离架构.md" --stats
python scripts/extract_body.py "src/计算与储存分离架构.md" --stdout
```

### 第三步：生成音频

edge-tts 无需密钥，直接运行：

```bash
# 合成全部 src/ 文档（输出到 audio/ 目录）
python scripts/tts_edge.py

# 合成单篇
python scripts/tts_edge.py --file "src/计算与储存分离架构.md"

# 切换音色（默认晓晓女声）
python scripts/tts_edge.py --voice zh-CN-YunxiNeural

# 调整语速（-50% ~ +100%）
python scripts/tts_edge.py --rate -10%
```

查看可用音色：

```bash
python scripts/tts_edge.py --list-voices
```

### 第四步：验证输出

1. 检查 `audio/` 目录，确认每个 .md 都有对应的 .mp3
2. 抽查 1～2 个文件播放，确认音质和朗读流畅度
3. 如有失败——通常是网络问题，重试即可

### 可靠中文音色

| 名称 | 描述 |
|------|------|
| `zh-CN-XiaoxiaoNeural` | 晓晓（女声，活泼，默认） |
| `zh-CN-YunxiNeural` | 云希（男声） |
| `zh-CN-YunyangNeural` | 云扬（男声，新闻播报风） |
| `zh-CN-XiaohanNeural` | 晓涵（女声，温暖） |
| `zh-CN-XiaochenNeural` | 晓辰（女声，自然） |

## 备选方案（腾讯云 TTS）

如需使用腾讯云付费接口，参考 `scripts/tts_tencent.py`，需提供 SecretId/SecretKey：

```bash
export TENCENT_SECRET_ID="your-secret-id"
export TENCENT_SECRET_KEY="your-secret-key"
python scripts/tts_tencent.py
```

密钥申请地址：https://console.cloud.tencent.com/cam/capi

## 关键规则

1. **只朗读正文**：标题（#）和记忆线/题干（>）不朗读
2. **优先 edge-tts**：免费、无需账号、即装即用
3. **无需分段**：论文正文 2000~3000 字符，edge-tts 无字符上限

## 输出说明

完成后向用户汇报：
- 合成了几篇文档
- 每篇的字符数和音频文件大小
- 输出目录位置
- 失败的篇目及原因
