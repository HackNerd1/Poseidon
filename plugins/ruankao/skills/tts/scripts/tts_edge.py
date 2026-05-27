# -*- coding: utf-8 -*-
"""edge-tts 论文文本转语音脚本 (免费, 无需密钥)

读取 src/ 目录下的 Markdown 论文文件，自动提取正文（过滤标题和引用行），
通过 Microsoft Edge TTS 生成 mp3 音频。

edge-tts 通过 Edge 浏览器的公开接口调用微软神经语音引擎，
与 Azure 付费版同款音质，完全免费且无需注册。

用法示例:
  # 合成全部 src/ 下的文档
  python tts_edge.py

  # 合成单篇
  python tts_edge.py --file "../src/计算与储存分离架构.md"

  # 指定音色和语速
  python tts_edge.py --voice zh-CN-YunxiNeural --rate +10%

  # 自定义输出目录
  python tts_edge.py --output-dir "../mp3"
"""

import sys
import io
import argparse
import asyncio
from pathlib import Path

import edge_tts

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 默认音色: 晓晓（女声，中文普通话）
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

# 可选中文音色速查
VOICE_LIST = {
    "zh-CN-XiaoxiaoNeural": "晓晓（女声，活泼）",
    "zh-CN-YunxiNeural":    "云希（男声）",
    "zh-CN-YunjianNeural":  "云健（男声，新闻播报）",
    "zh-CN-XiaoyiNeural":   "晓伊（女声，温柔）",
    "zh-CN-YunyangNeural":  "云扬（男声，新闻播报）",
    "zh-CN-XiaochenNeural": "晓辰（女声，自然）",
    "zh-CN-XiaohanNeural":  "晓涵（女声，温暖）",
    "zh-CN-XiaozhenNeural": "晓臻（女声，沉稳）",
    "zh-CN-YunfengNeural":  "云枫（男声，低沉）",
}


def extract_body(md_path):
    """从 Markdown 文件提取正文（过滤 # 标题行和 > 引用行）"""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    body_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('#'):
            continue
        if stripped.startswith('>'):
            continue
        body_lines.append(stripped)

    return '\n'.join(body_lines)


def find_md_files(src_dir):
    """查找目录下所有 .md 文件，按文件名排序"""
    src_path = Path(src_dir)
    if not src_path.exists():
        print(f"[错误] 目录不存在: {src_dir}")
        sys.exit(1)
    files = sorted(src_path.glob('*.md'))
    if not files:
        print(f"[错误] {src_dir} 下未找到 .md 文件")
        sys.exit(1)
    return files


async def synthesize(text, voice, rate, output_path):
    """调用 edge-tts 合成语音并保存为 mp3"""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
    )
    await communicate.save(str(output_path))


async def process_file(md_path, voice, rate, output_dir):
    """处理单个文件：提取正文 → TTS → 保存 mp3"""
    name = md_path.stem
    body = extract_body(md_path)
    char_count = len(body)

    if char_count == 0:
        return False, "无正文"

    output_path = output_dir / f"{name}.mp3"

    try:
        await synthesize(body, voice, rate, output_path)
        size = output_path.stat().st_size
        return True, f"{size/1024:.1f} KB"
    except Exception as e:
        return False, str(e)


async def main_async(args):
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    src_dir = Path(args.src_dir) if args.src_dir else project_dir / 'src'
    output_dir = Path(args.output_dir) if args.output_dir else project_dir / 'audio'
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        md_files = [Path(args.file).resolve()]
    else:
        md_files = find_md_files(src_dir)

    if not md_files:
        print("[错误] 未找到 .md 文件")
        return

    voice_label = VOICE_LIST.get(args.voice, args.voice)

    print("=" * 60)
    print("  edge-tts 论文转语音 (免费)")
    print("=" * 60)
    print(f"  待处理: {len(md_files)} 篇")
    print(f"  音色:   {voice_label}")
    print(f"  语速:   {args.rate}")
    print(f"  输出:   {output_dir}")
    print("=" * 60)
    print()

    success = 0
    failed = []

    for i, md_path in enumerate(md_files, 1):
        name = md_path.stem
        body = extract_body(md_path)
        char_count = len(body)

        print(f"[{i}/{len(md_files)}] {name} ({char_count} 字符)", end="", flush=True)

        if char_count == 0:
            print(" - 跳过（无正文）")
            failed.append((name, "无正文"))
            continue

        ok, info = await process_file(md_path, args.voice, args.rate, output_dir)

        if ok:
            print(f" - {info}")
            success += 1
        else:
            print(f" - 失败: {info}")
            failed.append((name, info))

    print()
    print("=" * 60)
    print(f"  完成: {success}/{len(md_files)} 篇")
    if failed:
        print(f"  失败 {len(failed)} 篇:")
        for name, reason in failed:
            print(f"    - {name}: {reason}")
    else:
        print("  全部合成成功")
    print(f"  音频目录: {output_dir}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='edge-tts —— 免费将 src/ 论文文档转语音 (mp3)'
    )
    parser.add_argument(
        '--file', default=None,
        help='指定单个 .md 文件（默认处理 src/ 下全部）'
    )
    parser.add_argument(
        '--src-dir', default=None,
        help='源文件目录（默认 ../src）'
    )
    parser.add_argument(
        '--output-dir', default=None,
        help='音频输出目录（默认 ../audio）'
    )
    parser.add_argument(
        '--voice', default=DEFAULT_VOICE,
        help=f'音色名称（默认 {DEFAULT_VOICE} 晓晓女声）'
    )
    parser.add_argument(
        '--rate', default='+0%',
        help='语速（默认 +0%%，范围 -50%% ~ +100%%）'
    )
    parser.add_argument(
        '--list-voices', action='store_true',
        help='列出可用的中文音色'
    )

    args = parser.parse_args()

    if args.list_voices:
        print("可用中文音色:")
        for vid, label in VOICE_LIST.items():
            marker = " (默认)" if vid == DEFAULT_VOICE else ""
            print(f"  {vid}{marker}: {label}")
        return

    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
