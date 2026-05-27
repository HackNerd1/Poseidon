# -*- coding: utf-8 -*-
"""腾讯云 TTS 文本转语音脚本

读取 src/ 目录下的 Markdown 论文文件，自动提取正文（过滤标题和引用行），
调用腾讯云长文本 TTS API (CreateTtsTask) 生成 mp3 音频。

用法示例:
  # 合成全部 src/ 下的文档
  python tts_tencent.py --secret-id <SECRET_ID> --secret-key <SECRET_KEY>

  # 合成单篇
  python tts_tencent.py --secret-id <ID> --secret-key <KEY> --file "../src/计算与储存分离架构.md"

  # 使用环境变量
  $env:TENCENT_SECRET_ID = "xxx"
  $env:TENCENT_SECRET_KEY = "xxx"
  python tts_tencent.py

  # 指定音色和语速
  python tts_tencent.py --secret-id <ID> --secret-key <KEY> --voice-type 1002 --speed -1
  python tts_tencent.py --secret-id <ID> --secret-key <KEY> --output-dir "../mp3"

API 说明:
  - 长文本 TTS (CreateTtsTask): 单次支持 100,000 字符，异步返回，适合论文朗读
  - 短文本 TTS (TextToVoice): 单次最多 500 字符，同步返回，适合短句播报
  本脚本使用长文本接口。
"""

import os
import sys
import io
import json
import hashlib
import hmac
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# 支持 Windows 控制台 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ========== 常量 ==========
SERVICE = "tts"
HOST = "tts.tencentcloudapi.com"
REGION = "ap-guangzhou"
VERSION = "2019-08-23"
ALGORITHM = "TC3-HMAC-SHA256"

# 长文本 TTS 单次最大字符数
MAX_TEXT_LENGTH = 100000

# 轮询配置
POLL_INTERVAL = 3   # 轮询间隔（秒）
MAX_WAIT = 600      # 最大等待时间（秒）

# 默认音色：智瑜（标准女声）
DEFAULT_VOICE_TYPE = 1001

# 音色速查表
VOICE_MAP = {
    1001: "智瑜（标准女声）",
    1002: "智琪（标准女声）",
    1003: "智梦（标准女声）",
    1050: "WeNan（女声）",
    1051: "WeXi（男声）",
}


# ========== 正文提取 ==========
def extract_body(md_path):
    """从 Markdown 文件提取正文（过滤 # 标题行和 > 引用行）。

    规则:
    - 跳过空行
    - 跳过以 # 开头的标题行
    - 跳过以 > 开头的引用行（记忆线、题干）
    - 保留其余行为正文，用换行合并
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


# ========== 腾讯云 API v3 签名 (TC3-HMAC-SHA256) ==========
def _sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def tc3_sign(secret_id, secret_key, action, payload):
    """生成 TC3-HMAC-SHA256 签名。

    参考: https://cloud.tencent.com/document/api/1073/57368
    """
    timestamp = int(time.time())
    date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')

    # Step 1: 构造规范请求串
    http_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    content_type = "application/json; charset=utf-8"
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{HOST}\n"
        f"x-tc-action:{action.lower()}\n"
    )
    signed_headers = "content-type;host;x-tc-action"
    hashed_payload = hashlib.sha256(payload.encode('utf-8')).hexdigest()

    canonical_request = (
        f"{http_method}\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{hashed_payload}"
    )

    # Step 2: 构造待签名字符串
    credential_scope = f"{date}/{SERVICE}/tc3_request"
    hashed_canonical_request = hashlib.sha256(
        canonical_request.encode('utf-8')
    ).hexdigest()

    string_to_sign = (
        f"{ALGORITHM}\n"
        f"{timestamp}\n"
        f"{credential_scope}\n"
        f"{hashed_canonical_request}"
    )

    # Step 3: 计算签名
    secret_date = _sign(("TC3" + secret_key).encode('utf-8'), date)
    secret_service = _sign(secret_date, SERVICE)
    secret_signing = _sign(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing,
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Step 4: 构造 Authorization
    authorization = (
        f"{ALGORITHM} "
        f"Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    return authorization, timestamp


def call_tencent_api(secret_id, secret_key, action, params):
    """调用腾讯云 API，返回 JSON 响应"""
    payload = json.dumps(params, ensure_ascii=False)
    authorization, timestamp = tc3_sign(secret_id, secret_key, action, payload)

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": HOST,
        "X-TC-Action": action,
        "X-TC-Version": VERSION,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Region": REGION,
    }

    req = urllib.request.Request(
        f"https://{HOST}/",
        data=payload.encode('utf-8'),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return json.loads(error_body)
    except Exception as e:
        return {"Response": {"Error": {"Code": "NetworkError", "Message": str(e)}}}


def _check_api_error(resp):
    """检查 API 响应是否包含错误，有则抛出 RuntimeError"""
    if "Response" not in resp:
        raise RuntimeError(f"API 响应格式异常: {json.dumps(resp, ensure_ascii=False)}")
    if "Error" in resp["Response"]:
        error = resp["Response"]["Error"]
        raise RuntimeError(
            f"[{error.get('Code', 'Unknown')}] {error.get('Message', '未知错误')}"
        )


# ========== TTS 核心 ==========
def create_tts_task(secret_id, secret_key, text, voice_type, speed, volume):
    """创建长文本 TTS 合成任务。

    返回 TaskId。
    """
    params = {
        "Text": text,
        "VoiceType": voice_type,
        "PrimaryLanguage": 1,   # 1=中文
        "Codec": "mp3",
        "Speed": speed,
        "Volume": volume,
        "SampleRate": 16000,
    }

    resp = call_tencent_api(secret_id, secret_key, "CreateTtsTask", params)
    _check_api_error(resp)

    task_id = resp["Response"].get("Data", {}).get("TaskId")
    if not task_id:
        raise RuntimeError(f"未获取到 TaskId: {json.dumps(resp, ensure_ascii=False)}")
    return task_id


def poll_task_status(secret_id, secret_key, task_id):
    """轮询任务状态直到完成，返回音频下载 URL。

    Status 定义:
      0 - 任务等待
      1 - 任务执行中
      2 - 任务成功
      3 - 任务失败
    """
    elapsed = 0

    while elapsed < MAX_WAIT:
        params = {"TaskId": task_id}
        resp = call_tencent_api(secret_id, secret_key, "DescribeTtsTaskStatus", params)
        _check_api_error(resp)

        data = resp["Response"].get("Data", {})
        status = data.get("Status", -1)
        status_str = data.get("StatusStr", "未知")

        if status == 2:
            result_url = data.get("ResultUrl")
            if not result_url:
                raise RuntimeError("任务完成但未返回 ResultUrl")
            return result_url

        if status == 3:
            raise RuntimeError(
                f"合成失败: {data.get('ErrorMessage', status_str)}"
            )

        elapsed += POLL_INTERVAL
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"任务 {task_id} 超时（已等待 {MAX_WAIT}s）")


def download_audio(url, output_path):
    """从 URL 下载音频文件到本地"""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()

    with open(output_path, 'wb') as f:
        f.write(data)

    return len(data)


# ========== 主流程 ==========
def main():
    parser = argparse.ArgumentParser(
        description='腾讯云 TTS —— 将 src/ 论文文档转语音 (mp3)'
    )
    parser.add_argument(
        '--secret-id', default=os.environ.get('TENCENT_SECRET_ID'),
        help='腾讯云 SecretId（也可通过环境变量 TENCENT_SECRET_ID 设置）'
    )
    parser.add_argument(
        '--secret-key', default=os.environ.get('TENCENT_SECRET_KEY'),
        help='腾讯云 SecretKey（也可通过环境变量 TENCENT_SECRET_KEY 设置）'
    )
    parser.add_argument(
        '--src-dir', default=None,
        help='源文件目录（默认脚本所在目录的上级 ../src）'
    )
    parser.add_argument(
        '--output-dir', default=None,
        help='音频输出目录（默认脚本所在目录的上级 ../audio）'
    )
    parser.add_argument(
        '--file', default=None,
        help='指定单个 .md 文件（而非全部 src/）'
    )
    parser.add_argument(
        '--voice-type', type=int, default=DEFAULT_VOICE_TYPE,
        help=f'音色 ID: 1001=智瑜(女) 1002=智琪(女) 1003=智梦(女) 1050=WeNan(女) 1051=WeXi(男) (默认 {DEFAULT_VOICE_TYPE})'
    )
    parser.add_argument(
        '--speed', type=float, default=0,
        help='语速 -2~6 (0=1.0x, 2=1.5x, -2=0.8x, 默认 0)'
    )
    parser.add_argument(
        '--volume', type=float, default=5,
        help='音量 0~10 (默认 5)'
    )
    parser.add_argument(
        '--max-wait', type=int, default=MAX_WAIT,
        help=f'任务最大等待秒数 (默认 {MAX_WAIT})'
    )

    args = parser.parse_args()

    # 校验密钥
    if not args.secret_id or not args.secret_key:
        print("[错误] 请提供 --secret-id 和 --secret-key，或设置环境变量")
        print("  $env:TENCENT_SECRET_ID = \"your-secret-id\"")
        print("  $env:TENCENT_SECRET_KEY = \"your-secret-key\"")
        sys.exit(1)

    # 路径解析
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    src_dir = Path(args.src_dir) if args.src_dir else project_dir / 'src'
    output_dir = Path(args.output_dir) if args.output_dir else project_dir / 'audio'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 确定待处理文件
    if args.file:
        md_files = [Path(args.file).resolve()]
    else:
        md_files = find_md_files(src_dir)

    if not md_files:
        print("[错误] 未找到任何待处理的 .md 文件")
        sys.exit(1)

    voice_name = VOICE_MAP.get(args.voice_type, f"ID={args.voice_type}")

    print("=" * 60)
    print("  腾讯云 TTS 论文转语音")
    print("=" * 60)
    print(f"  待处理: {len(md_files)} 篇")
    print(f"  音色:   {voice_name}")
    print(f"  语速:   {args.speed} (倍率: {1 + args.speed * 0.25:.2f}x)")
    print(f"  音量:   {args.volume}/10")
    print(f"  输出:   {output_dir}")
    print(f"  最大文本: {MAX_TEXT_LENGTH:,} 字符/篇")
    print("=" * 60)
    print()

    success = 0
    failed = []

    for i, md_path in enumerate(md_files, 1):
        name = md_path.stem
        print(f"[{i}/{len(md_files)}] {name}")

        # 提取正文
        body = extract_body(md_path)
        char_count = len(body)
        print(f"  正文: {char_count} 字符", end="")

        if char_count == 0:
            print(" → 跳过（无正文）")
            failed.append((name, "无正文内容"))
            continue

        if char_count > MAX_TEXT_LENGTH:
            print(f" → 跳过（超出 {MAX_TEXT_LENGTH} 字符限制）")
            failed.append((name, f"超限 ({char_count}/{MAX_TEXT_LENGTH})"))
            continue

        print()

        # 创建 TTS 任务
        try:
            task_id = create_tts_task(
                args.secret_id, args.secret_key,
                body,
                voice_type=args.voice_type,
                speed=args.speed,
                volume=args.volume,
            )
            print(f"  任务ID: {task_id}")
        except Exception as e:
            print(f"  创建任务失败: {e}")
            failed.append((name, f"创建: {e}"))
            continue

        # 轮询结果
        try:
            print(f"  轮询中", end="", flush=True)
            result_url = poll_task_status(args.secret_id, args.secret_key, task_id)
            print(" → 完成")
        except Exception as e:
            print(f"\n  合成失败: {e}")
            failed.append((name, f"合成: {e}"))
            continue

        # 下载音频
        output_path = output_dir / f"{name}.mp3"
        try:
            print(f"  下载中", end="", flush=True)
            size = download_audio(result_url, output_path)
            print(f" → {output_path} ({size/1024:.1f} KB)")
            success += 1
        except Exception as e:
            print(f"\n  下载失败: {e}")
            failed.append((name, f"下载: {e}"))

        print()

    # 汇总
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


if __name__ == '__main__':
    main()
