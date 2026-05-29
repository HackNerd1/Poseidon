#!/usr/bin/env python3

"""
LeetCode Problem Initializer

Usage: python init-problem.py <leetcode-url> [base-dir] [--lang=typescript]

Fetches problem metadata from LeetCode GraphQL API and creates a local
solution file with problem description as comments and an empty function stub.
"""

import argparse
import json
import os
import re
import sys
import textwrap
import urllib.request
from html import unescape

# ── Language config ────────────────────────────────────────────────

LANG_CONFIG = {
    'typescript':  {'ext': '.ts',    'langSlug': 'typescript', 'comment': ('/**', ' * ', ' */')},
    'javascript':  {'ext': '.js',    'langSlug': 'javascript', 'comment': ('/**', ' * ', ' */')},
    'python3':     {'ext': '.py',    'langSlug': 'python3',    'comment': ('"""', '',   '"""')},
    'python':      {'ext': '.py',    'langSlug': 'python',     'comment': ('"""', '',   '"""')},
    'java':        {'ext': '.java',  'langSlug': 'java',       'comment': ('/**', ' * ', ' */')},
    'cpp':         {'ext': '.cpp',   'langSlug': 'cpp',        'comment': ('/**', ' * ', ' */')},
    'c':           {'ext': '.c',     'langSlug': 'c',          'comment': ('/**', ' * ', ' */')},
    'csharp':      {'ext': '.cs',    'langSlug': 'csharp',     'comment': ('/**', ' * ', ' */')},
    'go':          {'ext': '.go',    'langSlug': 'golang',     'comment': ('/*',  ' * ', ' */')},
    'rust':        {'ext': '.rs',    'langSlug': 'rust',       'comment': ('/**', ' * ', ' */')},
    'kotlin':      {'ext': '.kt',    'langSlug': 'kotlin',     'comment': ('/**', ' * ', ' */')},
    'swift':       {'ext': '.swift', 'langSlug': 'swift',      'comment': ('/**', ' * ', ' */')},
}

# ── Tag → directory mapping (priority-ordered) ─────────────────────

TAG_TO_DIR = {
    'sliding-window':       'SlidingWindow',
    'array':                'Array',
    'two-pointers':         'DoublePointer',
    'dynamic-programming':  'DP',
    'backtracking':         'Backtrack',
    'binary-search':        'BinarySearch',
    'greedy':               'Greedy',
    'hash-table':           'Hash',
    'depth-first-search':   'DFS',
    'breadth-first-search': 'BFS',
    'graph':                'Graph',
    'tree':                 'Tree',
    'binary-tree':          'Tree',
    'heap':                 'Heap',
    'stack':                'Stack',
    'queue':                'Queue',
    'linked-list':          'LinkedList',
    'sorting':              'Sorting',
    'divide-and-conquer':   'DivideAndConquer',
    'bit-manipulation':     'BitManipulation',
    'union-find':           'UnionFind',
    'trie':                 'Trie',
    'design':               'Design',
    'math':                 'Math',
    'string':               'String',
}

TAG_PRIORITY = [
    'sliding-window', 'dynamic-programming', 'backtracking', 'greedy',
    'binary-search', 'divide-and-conquer', 'two-pointers',
    'depth-first-search', 'breadth-first-search', 'graph',
    'union-find', 'trie', 'tree', 'binary-tree',
    'heap', 'stack', 'queue',
    'linked-list', 'hash-table', 'sorting', 'bit-manipulation',
    'design', 'math', 'string', 'array',
]


def determine_dir(tags):
    for priority_tag in TAG_PRIORITY:
        for t in tags:
            if t.get('slug') == priority_tag:
                return TAG_TO_DIR[priority_tag]
    return 'General'


# ── GraphQL request ─────────────────────────────────────────────────

def graphql_request(host, slug, payload):
    url = f'https://{host}/graphql'
    data = json.dumps(payload).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Content-Length': str(len(data)),
            'User-Agent': 'Mozilla/5.0 (compatible; AlgoCoach/1.0)',
            'Referer': f'https://{host}/problems/{slug}/',
            'Accept': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise SystemExit(f'HTTP {e.code}: {e.reason}')
    except urllib.error.URLError as e:
        raise SystemExit(f'Network error: {e.reason}')


def fetch_problem(host, slug):
    query = """
        query questionData($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionFrontendId
                title
                titleSlug
                difficulty
                content
                topicTags { name slug }
                codeSnippets { langSlug code }
            }
        }
    """
    result = graphql_request(host, slug, {
        'query': query,
        'variables': {'titleSlug': slug},
    })

    if 'errors' in result:
        raise SystemExit(f"GraphQL error: {result['errors'][0]['message']}")

    question = result.get('data', {}).get('question')
    if not question:
        raise SystemExit(
            f'Problem "{slug}" not found on {host}. Check the URL is correct.'
        )

    return question


# ── HTML → plain text ───────────────────────────────────────────────

def html_to_text(html_str):
    if not html_str:
        return ''

    text = html_str

    # Decode named HTML entities
    text = unescape(text)

    # Handle superscript / subscript
    text = re.sub(r'<sup>(\d+)</sup>', r'^\1', text)
    text = re.sub(r'<sub>(\d+)</sub>', r'_\1', text)

    # <pre> blocks → code fences
    text = re.sub(r'<pre[^>]*>', '\n```\n', text)
    text = text.replace('</pre>', '\n```\n')

    # <code> → backtick
    text = text.replace('<code>', '`')
    text = text.replace('</code>', '`')

    # <li> → bullet
    text = re.sub(r'<li[^>]*>', '\n- ', text)
    text = text.replace('</li>', '')

    # <p> → paragraph break, <br> → newline
    text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # Inline formatting tags → plain text
    for tag in ('strong', 'em', 'b', 'i', 'ul', 'ol'):
        text = re.sub(rf'</?{tag}[^>]*>', '', text, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Normalize whitespace per-line
    lines = []
    for line in text.split('\n'):
        lines.append(re.sub(r'[ \t]+', ' ', line).strip())
    text = '\n'.join(lines)

    # Collapse 3+ blank lines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ── Word wrap ───────────────────────────────────────────────────────

def wrap_lines(text, width):
    result = []
    for paragraph in text.split('\n'):
        if paragraph == '':
            result.append('')
        elif paragraph.startswith('- ') or paragraph.startswith('```'):
            # Preserve special lines; wrap as needed
            result.extend(textwrap.wrap(paragraph, width, break_long_words=False)
                          or [paragraph])
        else:
            wrapped = textwrap.wrap(paragraph, width, break_long_words=False)
            result.extend(wrapped if wrapped else [paragraph])
    return result


# ── Build file content ──────────────────────────────────────────────

def extract_function_stub(code_snippets, lang_slug):
    # Exact match
    for s in code_snippets:
        if s.get('langSlug') == lang_slug:
            return s['code']

    # Fallbacks
    for fb in ('typescript', 'javascript', 'python3', 'python', 'java', 'cpp', 'c', 'golang', 'rust'):
        for s in code_snippets:
            if s.get('langSlug') == fb:
                return s['code']

    return None


def build_file_content(problem, text_str, lang_cfg, host, slug):
    comment_start, comment_prefix, comment_end = lang_cfg['comment']
    max_width = 78 - len(comment_prefix)

    lines = []

    # Header
    lines.append(comment_start)
    lines.append(f"{comment_prefix}{problem['title']}")
    lines.append(f"{comment_prefix}LeetCode #{problem['questionFrontendId']} · {problem['difficulty']}")
    lines.append(f"{comment_prefix}https://{host}/problems/{slug}/")
    lines.append(f"{comment_prefix}")

    # Description body
    for raw_line in text_str.split('\n'):
        for wrapped in wrap_lines(raw_line, max_width):
            if wrapped == '':
                lines.append(comment_prefix.rstrip())
            else:
                lines.append(f"{comment_prefix}{wrapped}")

    lines.append(f" {comment_end}")
    lines.append('')

    # Function stub
    stub = extract_function_stub(problem.get('codeSnippets', []), lang_cfg['langSlug'])
    if stub:
        lines.append(stub)
    else:
        fn_name = problem.get('titleSlug', 'solution')
        fn_name = fn_name.split('-')[0] + ''.join(
            w.capitalize() for w in fn_name.split('-')[1:]
        )
        lines.append(f'function {fn_name}(/* TODO */): void {{')
        lines.append('    ')
        lines.append('};')

    return '\n'.join(lines) + '\n'


# ── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Initialize a LeetCode problem file locally.'
    )
    parser.add_argument(
        'url',
        help='LeetCode problem URL (.com or .cn)',
    )
    parser.add_argument(
        'base_dir',
        nargs='?',
        default=os.path.join(os.getcwd(), 'src'),
        help='Target src directory (default: ./src)',
    )
    parser.add_argument(
        '--lang',
        default='typescript',
        choices=list(LANG_CONFIG.keys()),
        help='Programming language (default: typescript)',
    )
    args = parser.parse_args()

    # Parse URL
    m = re.match(r'^https?://leetcode\.(com|cn)/problems/([^/]+)', args.url)
    if not m:
        print('Invalid LeetCode URL.')
        print('Expected: https://leetcode.com/problems/<slug> or https://leetcode.cn/problems/<slug>')
        sys.exit(1)

    host_suffix, slug = m.group(1), m.group(2)
    host = f'leetcode.{host_suffix}'
    lang_cfg = LANG_CONFIG[args.lang]

    # Fetch problem data
    print(f'Fetching problem "{slug}" from {host}...')
    problem = fetch_problem(host, slug)

    topic_tags = problem.get('topicTags') or []
    tag_slugs = [t.get('slug', '') for t in topic_tags]

    print(f"  Title:      {problem['title']}")
    print(f"  Difficulty:  {problem['difficulty']}")
    print(f"  Tags:        {', '.join(tag_slugs) if tag_slugs else '(none)'}")

    # Determine target directory
    dir_name = determine_dir(topic_tags)
    target_dir = os.path.join(args.base_dir, dir_name)
    print(f"  Directory:   {dir_name}/")

    # Create directory if needed
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        print(f"  Created:     {target_dir}")

    # Build filename: (difficulty)slug.ext
    difficulty = problem['difficulty'].lower()
    filename = f"({difficulty}){slug}{lang_cfg['ext']}"
    filepath = os.path.join(target_dir, filename)

    # Check if file already exists
    if os.path.exists(filepath):
        print(f'\nError: File already exists: {filepath}')
        sys.exit(1)

    # Convert description and write file
    text_str = html_to_text(problem.get('content'))
    content = build_file_content(problem, text_str, lang_cfg, host, slug)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'\nCreated: {filepath}')
    print('Done.')


if __name__ == '__main__':
    main()
