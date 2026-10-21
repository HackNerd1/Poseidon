"""auto-apply 公共库：浏览器会话、拟人化操作、选择器、IO、台账。

选择器维护约定见 ../../references/boss-zhipin.md（Boss 改版后按该文档更新 SEL）。
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

# ---- 数据目录（登录态/台账/截图都在插件外，插件更新不丢数据）----
DATA_DIR = Path(os.environ.get("OUTREACH_DATA_DIR", Path.home() / ".poseidon" / "outreach"))
BOSS_DIR = DATA_DIR / "boss"
PROFILE_DIR = BOSS_DIR / "profile"
SHOT_DIR = BOSS_DIR / "screenshots"
CONFIG_PATH = DATA_DIR / "config.json"
DELIVERED_PATH = BOSS_DIR / "delivered.json"


def ensure_dirs() -> None:
    for d in (PROFILE_DIR, SHOT_DIR, BOSS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ---- 通用工具 ----
def rand_delay(range_sec: tuple[float, float]) -> float:
    """在区间内随机取秒数并休眠，返回实际秒数。"""
    s = random.uniform(*range_sec)
    time.sleep(s)
    return s


def read_json(path: str | Path, fallback: Any) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(fallback))


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def rotate_existing(path: str | Path) -> str | None:
    """写入前发现同名旧文件则轮转为 -HHMM 后缀，同日重跑不静默覆盖
    （2026-10-20：第二次运行覆盖了 screen 审计，阈值调优数据丢失）。
    返回轮转后的路径；无同名文件返回 None。"""
    p = Path(path)
    if not p.exists():
        return None
    stamp = time.strftime("%H%M")
    rotated = p.with_name(f"{p.stem}-{stamp}{p.suffix}")
    n = 1
    while rotated.exists():  # 同一分钟内多次重跑
        rotated = p.with_name(f"{p.stem}-{stamp}-{n}{p.suffix}")
        n += 1
    p.replace(rotated)
    return str(rotated)


# ---- 城市代码（常用，完整表见 references/boss-zhipin.md）----
CITIES = {
    "100010000": "全国", "101010100": "北京", "101020100": "上海", "101280100": "广州",
    "101280600": "深圳", "101210100": "杭州", "101270100": "成都", "101200100": "武汉",
    "101110100": "西安", "101190400": "南京", "101230200": "苏州", "101280900": "东莞",
}

# ---- 默认配置（config.json 不存在时以此为基础生成）----
DEFAULT_CONFIG: dict[str, Any] = {
    "platform": "boss",
    "keywords": [],
    "city": "100010000",
    "jobType": "",          # 招聘类型筛选（1903=兼职），空=全部（探针验证）
    "pages": 2,
    "dailyLimit": 50,        # 保守值，平台硬上限约 100
    "delaySec": [8, 20],     # 相邻投递间隔（秒，随机）
    "pauseEvery": 10,        # 每投 N 个长休息
    "pauseSec": [60, 180],   # 长休息时长（秒，随机）
    "blacklistCompanies": [],
    "blacklistKeywords": [],
    "autoConfirm": False,    # true 时跳过人工确认（不推荐）
    "headed": False,         # 浏览器前台显示；首次配置时确认并写入，之后搜索/投递都读这里，不再每步询问
}


# 必须由用户定过值的配置字段——缺了就拒绝 --config 并让 Claude 补问，不许用默认值蒙混：
# headed 后台/前台是账号级选择；兼职折算 hoursPerDay（每天工时）必须问用户，不得默认 8 小时
# （2026-10-20 用户反馈），salaryFloorDay 是 85% 硬切线的基础。skipInactiveDays 是死配置：
# 列表接口没有活跃天数，无从执行，残留只会误导（发现即打印 ignored 并忽略）。
CONFIG_MUST_ASK = ("headed",)
CONFIG_PARTTIME_REQUIRED = ("hoursPerDay", "salaryFloorDay")
CONFIG_DEAD_KEYS = ("skipInactiveDays",)


def config_gaps(raw: dict) -> tuple[list[str], list[str]]:
    """校验用户原始 config（合并 DEFAULT_CONFIG 之前，否则默认值会掩盖缺字段）。返回 (missing, ignored)。"""
    missing = [k for k in CONFIG_MUST_ASK if k not in raw]
    if str(raw.get("jobType", "") or "") == "1903":
        missing += [k for k in CONFIG_PARTTIME_REQUIRED if k not in raw]
    ignored = [k for k in CONFIG_DEAD_KEYS if k in raw]
    return missing, ignored


# Chrome cookie expires_utc：自 1601-01-01 UTC 起的微秒数
_CHROME_EPOCH = 11644473600


class CookieReadError(OSError):
    """profile 里有 cookie 库，但这次读不出来。不要当成未登录。"""


def sync_pw():
    """返回 patchright 的 sync_playwright。未安装则失败，不退回 Playwright。"""
    try:
        from patchright.sync_api import sync_playwright
    except ImportError as e:
        raise SystemExit(
            "NEED_PATCHRIGHT 未安装 patchright，已停止。"
            "Boss 会识别原生 Playwright 并打空白页，脚本不再回退。"
            "在技能目录执行: pip install -r scripts/requirements.txt"
        ) from e
    return sync_playwright()


# ---- 浏览器会话（持久化登录态 + 基础拟人化）----
BASE_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    # Boss 风控对数据中心/境外出口 IP 直接打空白页，必须直连（zhipin.com 为国内站，直连可达）
    "--no-proxy-server",
]


# 屏幕外窗口定位：保持有头浏览器指纹（无头模式被 Boss 风控识别，且 patchright
# 对 headless 不做反检测补丁），又不弹窗打扰用户——「后台运行」的实现方式
OFFSCREEN_POS = "--window-position=-32000,-32000"


def launch(pw, visible: bool = False):
    """pw 为 sync_pw() 的返回值；persistent context 自动保存登录态。

    - visible=False（默认）：有头引擎，窗口定位屏幕外，后台运行不弹窗
    - visible=True：正常前台窗口（扫码登录、人工观察投递过程用）
    - 只用本机 Chrome（channel=chrome）+ 无视口模拟。勿再叠加 add_init_script，
      那会变成检测向量。Chrome 或 patchright 缺失时直接失败。
    """
    ensure_dirs()
    arg_list = list(BASE_LAUNCH_ARGS)
    if not visible:
        arg_list.append(OFFSCREEN_POS)
    try:
        return pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel="chrome",
            no_viewport=True,
            headless=False,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=arg_list,
        )
    except Exception as e:
        msg = str(e).lower()
        if any(k in msg for k in ("chrome", "channel", "executable")):
            raise SystemExit(
                "CHROME_MISSING 无法启动本机 Google Chrome（channel=chrome）。"
                "请安装 Chrome，不要用捆绑 Chromium，也不要退回 Playwright。"
                f"原因: {type(e).__name__}: {e}"
            ) from e
        raise


def goto_guarded(page, url: str, retries: int = 2) -> str | None:
    """导航并检测 Boss 风控空白页（先加载后跳白）。返回 None 正常，否则返回诊断文案。"""
    for attempt in range(retries + 1):
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        for _ in range(6):  # 风控跳白通常在加载后几秒内发生
            time.sleep(1)
            if page.url.startswith("about:blank"):
                break
        text = body_text(page).strip()
        if not page.url.startswith("about:blank") and text:
            return None
        shot(page, f"blank-page-attempt{attempt}")
        if attempt < retries:
            print(f"[guard] 页面被风控打空（第{attempt + 1}次），重试中...")
            time.sleep(random.uniform(3, 6))
    return ("页面反复被重定向为空白（Boss 风控）。排查顺序："
            "1) 关闭代理/TUN 模式；2) 更换网络（如切手机热点）；3) 稍后再试（IP 可能已被临时限制）。"
            "截图见 screenshots/")


def first_page(ctx):
    return ctx.pages[0] if ctx.pages else ctx.new_page()


def has_login(ctx) -> bool:
    now = time.time()
    return any(c["name"] == "wt2" and c.get("expires", 0) > now
               for c in ctx.cookies("https://www.zhipin.com"))


def _cookie_db(profile: Path) -> Path | None:
    for rel in (("Default", "Network", "Cookies"), ("Default", "Cookies")):
        p = profile.joinpath(*rel)
        if p.is_file():
            return p
    return None


def read_wt2_expiry(profile: Path | None = None) -> float | None:
    """不启动浏览器，读 profile 里未过期的 wt2 到期时间（unix 秒）。

    没有 cookie 库或没有有效 wt2 时返回 None。
    库存在但读失败时抛 CookieReadError，调用方不要当成未登录。
    """
    root = Path(profile) if profile is not None else PROFILE_DIR
    db = _cookie_db(root)
    if db is None:
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "Cookies"
            shutil.copy2(db, dest)
            for ext in ("-wal", "-shm"):
                side = Path(str(db) + ext)
                if side.is_file():
                    shutil.copy2(side, Path(str(dest) + ext))
            con = sqlite3.connect(f"file:{dest}?mode=ro", uri=True)
            try:
                rows = con.execute(
                    "SELECT expires_utc, is_persistent FROM cookies "
                    "WHERE name = ? AND host_key LIKE ?",
                    ("wt2", "%zhipin.com"),
                ).fetchall()
            finally:
                con.close()
    except (OSError, sqlite3.Error) as e:
        raise CookieReadError(f"无法读取 {db}: {type(e).__name__}: {e}") from e
    now = time.time()
    best = None
    for expires_utc, is_persistent in rows:
        if not is_persistent or not expires_utc:
            continue
        unix = expires_utc / 1_000_000 - _CHROME_EPOCH
        if unix > now and (best is None or unix > best):
            best = unix
    return best


def profile_has_login(profile: Path | None = None) -> bool:
    """wt2 存在且未过期。不启动浏览器。读失败时抛 CookieReadError。"""
    return read_wt2_expiry(profile) is not None


# ---- 风控信号检测 ----
RISK_TEXT = re.compile(r"安全验证|请完成验证|验证码|异常操作|访问环境异常")
LIMIT_TEXT = re.compile(r"今日沟通.*上限|今日投递.*上限|已达上限|今天的机会已用完")


def body_text(page) -> str:
    try:
        return page.evaluate("() => document.body ? document.body.innerText : ''")
    except Exception:
        return ""


def editor_text(page) -> str:
    """聊天输入框（contenteditable）里的文字。整页 innerText 含输入框，校验发送状态前要剔除。"""
    try:
        return page.evaluate(
            "() => { const e = document.querySelector(\"[contenteditable='true']\");"
            " return e ? e.innerText : ''; }")
    except Exception:
        return ""


def history_text(page) -> str:
    """整页文本减去输入框文字：「打了还没发出去」的内容不算已发送，
    防止发送校验假阳性（2026-10-20 事故专档 4.1）。"""
    body = body_text(page)
    editor = editor_text(page)
    return body.replace(editor, "") if editor else body


def is_captcha(page) -> bool:
    return bool(RISK_TEXT.search(body_text(page)))


# 详情/聊天页专用：全文搜「验证码」会把 JD 正文提到「验证码」的岗位误判为风控
# （2026-10-19 赛琳贸易岗实测），改为只认 geetest 面板或真实风控弹层文案
RISK_TEXT_STRICT = re.compile(r"安全验证|异常操作|访问环境异常")


def is_captcha_strict(page) -> bool:
    try:
        loc = page.locator(".geetest_panel, .geetest_window, iframe[src*='geetest']")
        if loc.first.is_visible(timeout=400):
            return True
    except Exception:
        pass
    return bool(RISK_TEXT_STRICT.search(body_text(page)))


def is_daily_limit(page) -> bool:
    return bool(LIMIT_TEXT.search(body_text(page)))


# ---- 多候选选择器：依次尝试，返回首个可见 locator ----
# is_visible 的 timeout 参数不生效（瞬时检查），「等待」形同虚设（2026-10-20 投递 5/5
# error 的根因之一），必须用 wait_for 才是真等待
def find_visible(page, selectors: list[str], per_timeout: int = 1200):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=per_timeout)
            return loc
        except Exception:
            continue
    return None


def find_chat_input(ctx, selectors: list[str], per_timeout: int = 1500):
    """在所有标签页/iframe 里找聊天输入框，返回 (frame_or_page, locator) 或 (None, None)。

    点击「立即沟通/继续沟通」后当前标签页会 SPA 跳到 /web/geek/chat 路由
    （2026-10-20 实测：#chat-input 在主 frame，约 1s 可见）；首聊也可能走弹层或新标签，
    只用单一 page.locator 探测会漏。这里全量扫（跳过 about: 空 frame）。
    """
    for page in ctx.pages:
        for frame in page.frames:
            if frame.url.startswith("about:"):
                continue
            for sel in selectors:
                try:
                    loc = frame.locator(sel).first
                    loc.wait_for(state="visible", timeout=per_timeout)
                    return (frame, loc)
                except Exception:
                    continue
    return (None, None)


# ---- 选择器（详情/聊天页；多候选兜底改版）----
# 搜索页数据不走 DOM（接口拦截，见 references/boss-zhipin.md），此处仅详情/聊天选择器
SEL: dict[str, dict[str, list[str]]] = {
    "detail": {
        "jd": [".job-sec-text", ".job-detail-section", ".job-detail"],
        "start_chat": ["a.btn-startchat", "a[ka='job_detail_chat']", 'button:has-text("立即沟通")', 'a:has-text("立即沟通")'],
        "continue_chat": ['a.btn-startchat:has-text("继续沟通")', 'button:has-text("继续沟通")', 'a:has-text("继续沟通")'],
    },
    "chat": {
        "input": ["#chat-input", ".chat-input textarea", "div.chat-editor textarea", "[contenteditable='true'].chat-input", "div.edit-area [contenteditable='true']", "[contenteditable='true']"],
        "send": ["button.btn-send", 'button:has-text("发送")', ".chat-op button[type='submit']"],
    },
}

def dump_frame_diag(ctx, tag: str) -> str:
    """把所有标签页/iframe 的 URL、聊天候选选择器命中数、正文前 1500 字落 JSON。

    用途：apply 阶段「未找到聊天输入框」时，截图没法被脚本回读分析，这份 JSON 才能定位
    是选择器过时还是路由变化（2026-10-20 事故改进项）。返回文件路径。"""
    pages = []
    for page in ctx.pages:
        entry: dict[str, Any] = {"url": page.url[:200], "frames": []}
        for frame in page.frames:
            if frame.url.startswith("about:"):
                continue
            hits: dict[str, int] = {}
            for sel in SEL["chat"]["input"] + SEL["chat"]["send"]:
                try:
                    hits[sel] = frame.locator(sel).count()
                except Exception:
                    hits[sel] = -1
            entry["frames"].append({"url": frame.url[:200], "selectorHits": hits})
        txt = body_text(page)
        if txt:
            entry["bodyTextHead"] = txt[:1500]
        pages.append(entry)
    ensure_dirs()
    diag_dir = BOSS_DIR / "diag"
    diag_dir.mkdir(parents=True, exist_ok=True)
    p = diag_dir / f"chat-{time.strftime('%Y%m%d-%H%M%S')}.json"
    write_json(p, {"tag": tag, "pages": pages})
    return str(p)


# ---- 截图（出错/风控留证）----
def shot(page, name: str) -> str:
    ensure_dirs()
    p = SHOT_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{name}.png"
    try:
        page.screenshot(path=str(p))
    except Exception:
        pass
    return str(p)


# ---- 拟人化输入（逐字符，30-90ms/字符）----
def human_type(locator, text: str) -> None:
    locator.click()
    time.sleep(random.uniform(0.3, 0.7))
    locator.press_sequentially(text, delay=random.randint(30, 90))


# ---- 薪资解析 → 结构化 ----
# 两类口径：K 月薪「25-50K·16薪」；兼职计件「40-70元/时」「200-300元/天」「2000-3500元/周」「3000-5000元/月」。
# 兼职四类在 2026-10-20 实测的 160 条兼职岗里占 100%（时77/天39/月39/周5），旧版只认 K 时全部返回 null。
def parse_salary(s: str) -> dict | None:
    """K 月薪返回 unit="K" + minK/maxK/months/annual*；计件返回 unit="时/天/周/月" + min/max（元/该单位）。
    单值（如「200元/天」）按 min=max 处理。解析不出返回 None（面议/未知格式），调用方按未知薪资处理。"""
    s = s or ""
    m = re.search(r"(\d+)(?:\s*-\s*(\d+))?\s*[Kk]", s)
    if m:
        mm = re.search(r"[·x](\d+)薪", s)
        months = int(mm.group(1)) if mm else 12
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        return {"unit": "K", "minK": lo, "maxK": hi, "months": months,
                "annualMinK": lo * months, "annualMaxK": hi * months}
    m = re.search(r"(\d+)(?:\s*-\s*(\d+))?\s*元\s*/\s*(天|日|时|小时|周|月)", s)
    if m:
        unit = {"日": "天", "小时": "时"}.get(m.group(3), m.group(3))
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        return {"unit": unit, "min": lo, "max": hi}
    return None


# JD 硬条件（2026-10-21）：列表字段没有 211/985、工时窗口。只扫详情全文，不靠模型翻 JD。
# 「硕士」必须带要求语境，避免技能描述里的偶然出现；「不限/无要求」不算窗口。
_SCHOOL_211 = re.compile(r"211|985|双一流")
_DEGREE_MASTER = re.compile(r"硕士(及以上|研究生|学历|学位)|硕士以上|要求硕士")
_WEEKLY_HOURS = re.compile(r"每周[^\n]{0,8}?(\d+)\s*小时")
_TIME_CLOCK = re.compile(r"\d{1,2}:\d{2}")
_TIME_WINDOW_LOOSE = re.compile(r"工作日\s*\d{1,2}\s*[-~到至]\s*\d{1,2}\s*点")
_TERM_NONE = ("不限", "无要求", "面议", "弹性", "")
_LONG_INACTIVE = re.compile(r"半年前|\d+\s*年前|一年前|1年前|\d+\s*月前|很久")

# 同日浏览器会话预算。search+detail 超过此次数后，execute/verify 必须先冷却。
# 批量 detail 一次进程只计 1 次（2026-10-21：8 次详情是频控主因）。
SESSION_BUDGET = 6
COOLDOWN_SEC = 180
_SESSION_KINDS = ("search", "detail", "apply", "verify")
REPLY_STATUSES = ("unread", "read", "replied", "no_reply")


def scan_jd_flags(text: str, terms: dict | None = None) -> list[str]:
    """从详情全文 + 兼职条款打硬条件标。无命中返回空列表。"""
    blob = text or ""
    terms = terms or {}
    flags: list[str] = []
    if _SCHOOL_211.search(blob):
        flags.append("school_211")
    if _DEGREE_MASTER.search(blob):
        flags.append("degree_master")
    weekly = (terms.get("每周工期") or "").strip()
    if weekly and weekly not in _TERM_NONE:
        flags.append("weekly_days")
    if _WEEKLY_HOURS.search(blob):
        flags.append("weekly_hours")
    work_time = (terms.get("工作时间") or "").strip()
    if work_time and work_time not in _TERM_NONE and _TIME_CLOCK.search(work_time):
        flags.append("time_window")
    elif _TIME_WINDOW_LOOSE.search(blob):
        flags.append("time_window")
    return flags


def hr_long_inactive(activity: str) -> bool:
    """「半年前/N月前活跃」视为长期不活跃。空串与「刚刚/本周/N日内」不是。"""
    return bool(_LONG_INACTIVE.search(activity or ""))


def deadline_expired(value: str, today: str | None = None) -> bool | None:
    """「招聘截止」值（如 '时间：2026-12-18' / '2026年8月25日'）是否已过期。
    解析不出日期返回 None（按未知处理，不判过期）。"""
    m = re.search(r"(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})", value or "")
    if not m:
        return None
    y, mo, d = (int(g) for g in m.groups())
    try:
        deadline = time.strptime(f"{y}-{mo}-{d}", "%Y-%m-%d")
    except ValueError:
        return None
    ref = time.strptime(today, "%Y-%m-%d") if today else time.localtime()
    return deadline < ref


# ---- 投递台账（防重投）----
def job_key(j: dict) -> str:
    m = re.search(r"job_detail/([^./?]+)", j.get("link", ""))
    return m.group(1) if m else f"{j.get('company', '')}|{j.get('job', '')}"


def load_delivered() -> dict:
    return read_json(DELIVERED_PATH, {"delivered": {}})


def mark_delivered(rec: dict) -> None:
    d = load_delivered()
    key = job_key(rec)
    prev = d["delivered"].get(key) or {}
    stored = {**rec, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    # 重投/补发不要抹掉已写下的回复状态（2026-10-21：台账此前没有 replyStatus 载体）
    if "replyStatus" not in rec:
        stored["replyStatus"] = prev.get("replyStatus")
    d["delivered"][key] = stored
    write_json(DELIVERED_PATH, d)


def note_verify(key: str, status: str, note: str, path: Path | None = None) -> None:
    """把 --verify 结果写回已有台账。没有这条投递记录时不新建。"""
    if not key:
        return
    dest = path or DELIVERED_PATH
    d = read_json(dest, {"delivered": {}})
    rec = (d.get("delivered") or {}).get(key)
    if not rec:
        return
    rec["verifyStatus"] = status
    rec["verifyNote"] = note
    rec["verifiedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    d["delivered"][key] = rec
    write_json(dest, d)


def set_reply_status(key: str, status: str, path: Path | None = None) -> str:
    """写 replyStatus。成功返回空串，否则返回 REPLY_STATUS_* 错误行。不启动浏览器。"""
    if status not in REPLY_STATUSES:
        return f"REPLY_STATUS_INVALID {status}（允许 {'/'.join(REPLY_STATUSES)}）"
    dest = path or DELIVERED_PATH
    d = read_json(dest, {"delivered": {}})
    rec = (d.get("delivered") or {}).get(key)
    if not rec:
        return f"REPLY_STATUS_MISSING {key}"
    rec["replyStatus"] = status
    rec["replyStatusAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    d["delivered"][key] = rec
    write_json(dest, d)
    return ""


def sessions_path(root: Path | None = None) -> Path:
    return (root or BOSS_DIR) / "sessions.json"


def record_session(kind: str, root: Path | None = None, at: str | None = None) -> None:
    """记一次已打开的浏览器会话。kind 为 search/detail/apply/verify。一次进程记一条。"""
    if kind not in _SESSION_KINDS:
        raise ValueError(f"unknown session kind: {kind}")
    path = sessions_path(root)
    day = (at or time.strftime("%Y-%m-%dT%H:%M:%S"))[:10]
    data = read_json(path, {})
    data.setdefault(day, []).append({"kind": kind, "at": at or time.strftime("%Y-%m-%dT%H:%M:%S")})
    write_json(path, data)


def read_sessions(root: Path | None = None, day: str | None = None) -> list[dict]:
    day = day or time.strftime("%Y-%m-%d")
    data = read_json(sessions_path(root), {})
    return list(data.get(day) or [])


def _parse_session_at(at: str) -> float:
    return time.mktime(time.strptime(at[:19], "%Y-%m-%dT%H:%M:%S"))


def cooldown_wait_sec(sessions: list[dict], now: float | None = None,
                      threshold: int = SESSION_BUDGET, need: int = COOLDOWN_SEC) -> float:
    """search+detail 次数超过 threshold 时，返回距离上次浏览器会话还要冷却的秒数。未超返回 0。"""
    opened = [s for s in sessions if s.get("kind") in ("search", "detail")]
    if len(opened) <= threshold:
        return 0.0
    times = []
    for s in sessions:
        if s.get("kind") not in _SESSION_KINDS or not s.get("at"):
            continue
        try:
            times.append(_parse_session_at(s["at"]))
        except ValueError:
            continue
    if not times:
        return float(need)
    now = time.time() if now is None else now
    return max(0.0, need - (now - max(times)))


def delivered_recently(key: str, days: int = 7) -> bool:
    rec = load_delivered()["delivered"].get(key)
    if not rec:
        return False
    try:
        return time.time() - time.mktime(time.strptime(rec["at"][:19], "%Y-%m-%dT%H:%M:%S")) < days * 86400
    except (KeyError, ValueError):
        return False


def delivered_today_count() -> int:
    today = time.strftime("%Y-%m-%d")
    return sum(1 for r in load_delivered()["delivered"].values() if r.get("at", "").startswith(today))

