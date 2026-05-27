# -*- coding: utf-8 -*-
"""论文正文提取工具

从 Markdown 论文文件中提取纯正文（过滤标题行和引用行），输出为 .txt 文件。
可作为调试或审查正文内容的独立工具使用。

用法:
  python extract_body.py <论文路径>
  python extract_body.py <论文路径> --output <输出路径>
  python extract_body.py <论文路径> --stdout

示例:
  python extract_body.py "../src/计算与储存分离架构.md"
  python extract_body.py "../src/计算与储存分离架构.md" --stdout
"""

import sys
import io
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def extract_body_text(md_path):
    """从 Markdown 文件提取正文行。

    过滤规则:
    - 空行 → 跳过
    - # / ## / ### → 跳过（标题）
    - > 开头 → 跳过（引用/记忆线/题干）
    - 其余 → 正文
    """
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

    return body_lines


def main():
    parser = argparse.ArgumentParser(
        description='从 Markdown 论文提取正文文本'
    )
    parser.add_argument('file', help='论文 .md 文件路径')
    parser.add_argument('--output', '-o', default=None,
                        help='输出 .txt 文件路径（默认：同目录同名的 _正文.txt）')
    parser.add_argument('--stdout', action='store_true',
                        help='直接输出到终端（不保存文件）')
    parser.add_argument('--stats', action='store_true',
                        help='仅显示字符统计，不输出正文内容')
    args = parser.parse_args()

    md_path = Path(args.file)
    if not md_path.exists():
        print(f"[错误] 文件不存在: {md_path}")
        sys.exit(1)

    body_lines = extract_body_text(md_path)
    body_text = '\n'.join(body_lines)
    char_count = len(body_text)
    line_count = len(body_lines)

    if args.stats:
        print(f"文件:   {md_path.name}")
        print(f"正文行: {line_count}")
        print(f"总字符: {char_count}")
        return

    if args.stdout:
        print(body_text)
        print(f"\n--- 共 {line_count} 行, {char_count} 字符 ---")
        return

    # 默认输出文件
    output_path = Path(args.output) if args.output else md_path.with_suffix('').parent / f"{md_path.stem}_正文.txt"
    output_path.write_text(body_text, encoding='utf-8')
    print(f"已提取正文 → {output_path}")
    print(f"共 {line_count} 行, {char_count} 字符")


if __name__ == '__main__':
    main()
