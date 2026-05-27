# -*- coding: utf-8 -*-
"""论文各段字数统计脚本

按 ## 和 ### 标题自动分段，统计每段的中文/数字/英文总字符数，
并与规范字数对比。

用法: python count_chars.py <论文文件路径> [段落名=目标字数 ...]
示例: python count_chars.py "../计算与储存分离架构.md" "摘要=300" "项目背景=500" "结尾=400"
"""

import re
import sys
import io

# 支持 Windows 控制台 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 容差
TOLERANCE = 30


def parse_targets(args):
    """从命令行参数解析目标字数: key=value"""
    targets = {}
    for arg in args:
        if '=' in arg:
            key, val = arg.split('=', 1)
            try:
                targets[key] = int(val)
            except ValueError:
                print(f"警告: 忽略无效参数 '{arg}'（值必须是整数）")
    return targets


def count_chars(text):
    """统计中文字符 + 数字 + 英文字母的总数"""
    chinese = len(re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text))
    digits  = len(re.findall(r'[0-9]', text))
    letters = len(re.findall(r'[a-zA-Z]', text))
    return chinese + digits + letters, chinese, digits, letters


def parse_sections(filepath):
    """按 ## / ### 标题将文件拆分为段"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sections = {}
    current = None
    buf = []

    for line in lines:
        stripped = line.strip()
        if line.startswith('### '):
            if current:
                sections[current] = ''.join(buf)
            current = stripped[4:]
            buf = []
        elif line.startswith('## '):
            if current:
                sections[current] = ''.join(buf)
            current = stripped[3:]
            buf = []
        elif current is not None and stripped and not stripped.startswith('> '):
            buf.append(line)

    if current:
        sections[current] = ''.join(buf)
    return sections


def main():
    if len(sys.argv) < 2:
        print("用法: python count_chars.py <论文文件路径> [段落名=目标字数 ...]")
        print('示例: python count_chars.py "../论文.md" "摘要=300" "项目背景=500" "结尾=400"')
        return

    filepath = sys.argv[1]
    targets = parse_targets(sys.argv[2:])

    sections = parse_sections(filepath)
    if not sections:
        print("未找到任何段落，请确认文件包含 ## 标题")
        return

    has_targets = len(targets) > 0
    total = 0
    for name, content in sections.items():
        cnt, ch, dg, lt = count_chars(content)
        total += cnt

        target = targets.get(name)
        if target is not None:
            diff = cnt - target
            flag = "OK" if abs(diff) <= TOLERANCE else "OVER"
            print(f"{name}: {cnt}字 (目标{target}, 差值{diff:+d}) [{flag}]")
        else:
            tag = " [无规范]" if has_targets else ""
            print(f"{name}: {cnt}字{tag}")
        print(f"  -> 中文{ch} + 数字{dg} + 英文{lt}")

    print(f"\n正文合计: {total}字")

    if has_targets:
        missing = set(targets) - set(sections.keys())
        if missing:
            print(f"\n警告: 以下段落标题未匹配到:", ', '.join(missing))
            print("请确认论文中的标题与参数中的 key 一致")


if __name__ == '__main__':
    main()
