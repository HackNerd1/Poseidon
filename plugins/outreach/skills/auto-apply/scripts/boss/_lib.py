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
import threading
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
    "city": "100010000",     # 地域过滤口径（100010000=全国，不按地域淘汰）
    "searchCities": [],      # 搜索城市集；远程/兼职常挂在具体城市，只搜全国会漏。空=只搜 city
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


# 后台窗口不使用负坐标。macOS 会把 --window-position=-32000 夹回工作区左上角，
# 再写回 profile，下次启动直接盖住画面（2026-10-21）。visible=False 改由 window_sink
# 把焦点还给当前应用。位置若配置了，启动时写进 Preferences 并用 CDP 再摆一次：
# 只传 --window-position 会被记住的 window_placement 盖掉。

WINDOW_KEYS = ("windowX", "windowY", "windowWidth", "windowHeight")
PRESET_NAMES = ("左上", "右上", "左下", "右下")
PRESET_MARGIN = 40
PRESET_WIDTH = 640
PRESET_HEIGHT = 800
MIN_WINDOW = 320
_FAR_COORD = 20000
_XY_RE = re.compile(r"^(-?\d+)\s*,\s*(-?\d+)(?:\s+(\d+)\s*[xX×]\s*(\d+))?$")


def _cg():
    """CoreGraphics，或 None。导入本模块时不碰系统框架。"""
    try:
        import ctypes
        from ctypes import POINTER, Structure, c_double, c_int32, c_uint32

        class CGPoint(Structure):
            _fields_ = [("x", c_double), ("y", c_double)]

        class CGSize(Structure):
            _fields_ = [("width", c_double), ("height", c_double)]

        class CGRect(Structure):
            _fields_ = [("origin", CGPoint), ("size", CGSize)]

        cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cg.CGMainDisplayID.restype = c_uint32
        cg.CGDisplayBounds.argtypes = [c_uint32]
        cg.CGDisplayBounds.restype = CGRect
        cg.CGGetOnlineDisplayList.argtypes = [c_uint32, POINTER(c_uint32), POINTER(c_uint32)]
        cg.CGGetOnlineDisplayList.restype = c_int32
        return cg, c_uint32
    except Exception:
        return None


def display_bounds() -> list[tuple[int, int, int, int]]:
    """在线显示器的 (x, y, w, h)，点坐标。读不到返回空列表。

    CGGetActiveDisplayList 在这台 Mac 上返回 0 块，在线列表才有主屏和副屏。
    """
    loaded = _cg()
    if not loaded:
        return []
    import ctypes
    cg, c_uint32 = loaded
    try:
        arr = (c_uint32 * 8)()
        count = c_uint32(0)
        err = cg.CGGetOnlineDisplayList(8, arr, ctypes.byref(count))
        rects = []
        if err == 0:
            for i in range(count.value):
                rect = cg.CGDisplayBounds(arr[i])
                w, h = int(rect.size.width), int(rect.size.height)
                if w > 0 and h > 0:
                    rects.append((int(rect.origin.x), int(rect.origin.y), w, h))
        if rects:
            return rects
        rect = cg.CGDisplayBounds(cg.CGMainDisplayID())
        w, h = int(rect.size.width), int(rect.size.height)
        if w > 0 and h > 0:
            return [(int(rect.origin.x), int(rect.origin.y), w, h)]
    except Exception:
        return []
    return []


def main_display_bounds() -> tuple[int, int, int, int] | None:
    """主屏点坐标。预设落在主屏，不落到副屏。"""
    loaded = _cg()
    if not loaded:
        return None
    cg, _ = loaded
    try:
        rect = cg.CGDisplayBounds(cg.CGMainDisplayID())
        w, h = int(rect.size.width), int(rect.size.height)
        if w <= 0 or h <= 0:
            return None
        return (int(rect.origin.x), int(rect.origin.y), w, h)
    except Exception:
        return None


def window_presets(bounds: tuple[int, int, int, int] | None = None) -> dict[str, dict]:
    """四角预设。bounds 缺省时读主屏；读不到返回空。"""
    if bounds is None:
        bounds = main_display_bounds()
    if not bounds:
        return {}
    x, y, w, h = bounds
    if w < MIN_WINDOW + 2 * PRESET_MARGIN or h < MIN_WINDOW + 2 * PRESET_MARGIN:
        return {}
    width = min(PRESET_WIDTH, w - 2 * PRESET_MARGIN)
    height = min(PRESET_HEIGHT, h - 2 * PRESET_MARGIN)
    top = y + PRESET_MARGIN
    left = x + PRESET_MARGIN
    right = x + w - width - PRESET_MARGIN
    bottom = y + h - height - PRESET_MARGIN
    size = {"width": width, "height": height}
    return {
        "左上": {"x": left, "y": top, **size},
        "右上": {"x": right, "y": top, **size},
        "左下": {"x": left, "y": bottom, **size},
        "右下": {"x": right, "y": bottom, **size},
    }


def _overlaps(spec: dict, displays: list[tuple[int, int, int, int]]) -> bool:
    w = spec.get("width") or 200
    h = spec.get("height") or 200
    for dx, dy, dw, dh in displays:
        ox = min(spec["x"] + w, dx + dw) - max(spec["x"], dx)
        oy = min(spec["y"] + h, dy + dh) - max(spec["y"], dy)
        if ox >= 80 and oy >= 80:
            return True
    return False


def _window_fits(spec: dict, displays: list[tuple[int, int, int, int]] | None) -> str | None:
    if spec.get("width") is not None and (
            spec["width"] < MIN_WINDOW or spec.get("height", 0) < MIN_WINDOW):
        return f"WINDOW_POSITION_INVALID 宽高至少 {MIN_WINDOW}"
    if not displays:
        if abs(spec["x"]) > _FAR_COORD or abs(spec["y"]) > _FAR_COORD:
            return ("WINDOW_POSITION_INVALID 坐标离屏幕太远。"
                    "macOS 会把负到屏幕外的窗口夹回左上角，不要写 -32000")
        return None
    if not _overlaps(spec, displays):
        return ("WINDOW_POSITION_INVALID 位置不在任何屏幕上。"
                "左侧副屏可以用小负值；-32000 会被 macOS 夹回主屏左上角，已拒绝")
    return None


def parse_window_value(raw: str, bounds: tuple[int, int, int, int] | None = None,
                       displays: list[tuple[int, int, int, int]] | None = None
                       ) -> tuple[dict | None, str | None]:
    """解析预设、x,y 或 x,y WxH。成功 (spec, None)，失败 (None, WINDOW_POSITION_INVALID...)。"""
    text = (raw or "").strip()
    if text in PRESET_NAMES:
        spec = window_presets(bounds).get(text)
        if not spec:
            return None, "WINDOW_POSITION_INVALID 读不到主屏，不能用预设。请给 x,y 或 x,y WxH"
        return dict(spec), None
    m = _XY_RE.match(text)
    if not m:
        return None, "WINDOW_POSITION_INVALID 需要 左上/右上/左下/右下、x,y、x,y WxH，或 clear"
    spec: dict = {"x": int(m.group(1)), "y": int(m.group(2))}
    if m.group(3):
        spec["width"] = int(m.group(3))
        spec["height"] = int(m.group(4))
    err = _window_fits(spec, displays)
    if err:
        return None, err
    return spec, None


def resolve_window(cfg: dict, displays: list[tuple[int, int, int, int]] | None = None
                   ) -> tuple[dict | None, str | None]:
    """从 config 读窗口。都没设返回 (None, None)。非法返回 (None, 错误行)。"""
    if not any(cfg.get(k) is not None for k in WINDOW_KEYS):
        return None, None
    if cfg.get("windowX") is None or cfg.get("windowY") is None:
        return None, "WINDOW_POSITION_INVALID windowX 与 windowY 必须一起设置"
    if (cfg.get("windowWidth") is None) != (cfg.get("windowHeight") is None):
        return None, "WINDOW_POSITION_INVALID windowWidth 与 windowHeight 必须一起设置"
    try:
        spec: dict = {"x": int(cfg["windowX"]), "y": int(cfg["windowY"])}
        if cfg.get("windowWidth") is not None:
            spec["width"] = int(cfg["windowWidth"])
            spec["height"] = int(cfg["windowHeight"])
    except (TypeError, ValueError):
        return None, "WINDOW_POSITION_INVALID 坐标必须是整数"
    err = _window_fits(spec, displays)
    if err:
        return None, err
    return spec, None


def apply_window_config(config_path: str | Path, raw: str, *,
                        displays: list[tuple[int, int, int, int]] | None = None,
                        bounds: tuple[int, int, int, int] | None = None,
                        probe: bool = True) -> str:
    """--set-window 的写回。clear 删字段。不算用户确认。"""
    text = (raw or "").strip()
    path = Path(config_path)
    cfg = read_json(path, {})
    if text == "clear":
        if not path.exists():
            return f"CONFIG_MISSING 没有可读的 config: {path}"
        for k in WINDOW_KEYS:
            cfg.pop(k, None)
        write_json(path, cfg)
        return "WINDOW_CLEARED 已取消固定位置，下次沿用 Chrome 记住的位置"
    if not path.exists():
        return f"CONFIG_MISSING 没有可读的 config: {path}。先完成首次配置再写弹窗位置"
    if probe:
        if displays is None:
            displays = display_bounds()
        if bounds is None and text in PRESET_NAMES:
            bounds = main_display_bounds()
    spec, err = parse_window_value(text, bounds=bounds, displays=displays)
    if err:
        return err
    cfg["windowX"] = spec["x"]
    cfg["windowY"] = spec["y"]
    if spec.get("width") and spec.get("height"):
        cfg["windowWidth"] = spec["width"]
        cfg["windowHeight"] = spec["height"]
    else:
        cfg.pop("windowWidth", None)
        cfg.pop("windowHeight", None)
    write_json(path, cfg)
    size = f" {spec['width']}x{spec['height']}" if spec.get("width") else ""
    return f"WINDOW_SET {spec['x']},{spec['y']}{size}"


def remembered_window(profile_dir: Path | None = None) -> dict | None:
    """只读 Preferences 的 window_placement。读失败返回 None，不碰其它字段。"""
    path = (Path(profile_dir) if profile_dir else PROFILE_DIR) / "Default" / "Preferences"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    wp = (data.get("browser") or {}).get("window_placement") or {}
    if not isinstance(wp, dict) or "left" not in wp or "top" not in wp:
        return None
    out = {"x": int(wp["left"]), "y": int(wp["top"])}
    if "right" in wp and "bottom" in wp:
        out["width"] = int(wp["right"]) - int(wp["left"])
        out["height"] = int(wp["bottom"]) - int(wp["top"])
    return out


def window_chromium_args(spec: dict) -> list[str]:
    args = [f"--window-position={int(spec['x'])},{int(spec['y'])}"]
    if spec.get("width") and spec.get("height"):
        args.append(f"--window-size={int(spec['width'])},{int(spec['height'])}")
    return args


def window_bounds_payload(spec: dict) -> dict:
    bounds = {"left": int(spec["x"]), "top": int(spec["y"]), "windowState": "normal"}
    if spec.get("width") and spec.get("height"):
        bounds["width"] = int(spec["width"])
        bounds["height"] = int(spec["height"])
    return bounds


def write_window_placement(profile_dir: Path, spec: dict) -> bool:
    """启动前改 window_placement，避免 Chrome 把上次夹回左上角的位置恢复回来。

    Preferences 不存在时不创建：残缺文件会被当成坏 profile。
    """
    path = Path(profile_dir) / "Default" / "Preferences"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[launch] WINDOW_PREFS_SKIP {type(e).__name__}")
        return False
    if not isinstance(data, dict):
        return False
    browser = data.get("browser")
    if not isinstance(browser, dict):
        browser = {}
        data["browser"] = browser
    wp = browser.get("window_placement")
    if not isinstance(wp, dict):
        wp = {}
    width = spec.get("width")
    height = spec.get("height")
    if width is None or height is None:
        if all(k in wp for k in ("left", "top", "right", "bottom")):
            width = int(wp["right"]) - int(wp["left"])
            height = int(wp["bottom"]) - int(wp["top"])
        else:
            width, height = PRESET_WIDTH, PRESET_HEIGHT
    wp = dict(wp)
    wp["left"] = int(spec["x"])
    wp["top"] = int(spec["y"])
    wp["right"] = int(spec["x"]) + int(width)
    wp["bottom"] = int(spec["y"]) + int(height)
    wp["maximized"] = False
    browser["window_placement"] = wp
    write_json(path, data)
    return True


def place_window(ctx, spec: dict) -> None:
    """会话恢复之后再摆一次。失败只打印，不中断投递。"""
    pages = getattr(ctx, "pages", None)
    page = pages[0] if pages else None
    if page is None:
        return
    try:
        session = ctx.new_cdp_session(page)
        info = session.send("Browser.getWindowForTarget")
        session.send("Browser.setWindowBounds", {
            "windowId": info["windowId"],
            "bounds": window_bounds_payload(spec),
        })
    except Exception as e:
        print(f"[launch] WINDOW_PLACE_FAILED {type(e).__name__}: {e}")


def launch(pw, visible: bool = False):
    """pw 为 sync_pw() 的返回值；persistent context 自动保存登录态。

    - visible=False：有头窗口留在当前应用下面，不抢焦点。不再用屏幕外负坐标。
    - visible=True：前台窗口（扫码登录、人工观察投递过程用）
    - config 里的 windowX/windowY 两种模式都摆到该位置。未设置则沿用 Chrome 记住的位置。
    - 只用本机 Chrome（channel=chrome）+ 无视口模拟。勿再叠加 add_init_script，
      那会变成检测向量。Chrome 或 patchright 缺失时直接失败。
    """
    ensure_dirs()
    arg_list = list(BASE_LAUNCH_ARGS)
    spec, err = resolve_window(read_json(CONFIG_PATH, {}), displays=display_bounds())
    if err:
        print(err)
        spec = None
    stop = threading.Event()
    if not visible:
        from window_sink import occlusion_arg, start_keep_behind
        arg_list.append(occlusion_arg())
        stop = start_keep_behind(PROFILE_DIR)
    if spec:
        arg_list.extend(window_chromium_args(spec))
        write_window_placement(PROFILE_DIR, spec)
    try:
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel="chrome",
            no_viewport=True,
            headless=False,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=arg_list,
        )
    except Exception as e:
        stop.set()
        msg = str(e).lower()
        if any(k in msg for k in ("chrome", "channel", "executable")):
            raise SystemExit(
                "CHROME_MISSING 无法启动本机 Google Chrome（channel=chrome）。"
                "请安装 Chrome，不要用捆绑 Chromium，也不要退回 Playwright。"
                f"原因: {type(e).__name__}: {e}"
            ) from e
        raise
    if spec:
        place_window(ctx, spec)
        size = f" {spec['width']}x{spec['height']}" if spec.get("width") else ""
        print(f"[launch] WINDOW_AT {spec['x']},{spec['y']}{size}")
    if not visible:
        orig_close = ctx.close

        def close(*args, **kwargs):
            stop.set()
            return orig_close(*args, **kwargs)

        ctx.close = close
        print("[launch] 后台窗口保持在当前应用下面，不抢焦点")
    return ctx


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

