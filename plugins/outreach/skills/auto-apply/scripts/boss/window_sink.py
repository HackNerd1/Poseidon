"""把本技能拉起的 Chrome 压到用户当前应用下面。

macOS 不允许别的进程改窗口层级（SLSSetWindowLevel 会被忽略，SLSOrderWindow 返回 1000）。
负的 --window-position 也会被夹回屏幕左上角。这里只做焦点归还：Chrome 一到最前面，
就把焦点还给用户正在用的应用，窗口留在那个应用下面，不隐藏、不最小化。
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path

_SINK_OCCLUSION = "--disable-features=CalculateNativeWinOcclusion"


def occlusion_arg() -> str:
    return _SINK_OCCLUSION


def front_app_pid() -> int | None:
    """最前面的普通窗口（layer 0）所属进程。只读。"""
    try:
        import ctypes
        from ctypes import c_bool, c_char_p, c_int, c_long, c_uint32, c_void_p

        cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]
        cf.CFStringCreateWithCString.restype = c_void_p
        cf.CFArrayGetCount.argtypes = [c_void_p]
        cf.CFArrayGetCount.restype = c_long
        cf.CFArrayGetValueAtIndex.argtypes = [c_void_p, c_long]
        cf.CFArrayGetValueAtIndex.restype = c_void_p
        cf.CFDictionaryGetValue.argtypes = [c_void_p, c_void_p]
        cf.CFDictionaryGetValue.restype = c_void_p
        cf.CFNumberGetValue.argtypes = [c_void_p, c_int, c_void_p]
        cf.CFNumberGetValue.restype = c_bool
        cg.CGWindowListCopyWindowInfo.argtypes = [c_uint32, c_uint32]
        cg.CGWindowListCopyWindowInfo.restype = c_void_p
        key_pid = cf.CFStringCreateWithCString(None, b"kCGWindowOwnerPID", 0x08000100)
        key_layer = cf.CFStringCreateWithCString(None, b"kCGWindowLayer", 0x08000100)
        arr = cg.CGWindowListCopyWindowInfo(1, 0)
        if not arr:
            return None
        for i in range(cf.CFArrayGetCount(arr)):
            item = cf.CFArrayGetValueAtIndex(arr, i)
            layer_ref = cf.CFDictionaryGetValue(item, key_layer)
            layer = c_int()
            if not layer_ref or not cf.CFNumberGetValue(layer_ref, 3, ctypes.byref(layer)):
                continue
            if layer.value != 0:
                continue
            pid_ref = cf.CFDictionaryGetValue(item, key_pid)
            pid = c_int()
            if pid_ref and cf.CFNumberGetValue(pid_ref, 3, ctypes.byref(pid)):
                return int(pid.value)
    except Exception:
        return None
    return None


def profile_chrome_pids(profile_dir: Path) -> list[int]:
    """只匹配本技能 profile 的 Chrome，不动用户自己的 Chrome。"""
    marker = str(profile_dir)
    try:
        out = subprocess.check_output(["ps", "-ax", "-o", "pid=,command="], text=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    pids: list[int] = []
    for line in out.splitlines():
        line = line.strip()
        if marker not in line or "Google Chrome" not in line:
            continue
        try:
            pids.append(int(line.split(None, 1)[0]))
        except ValueError:
            continue
    return pids


def demote_chrome(profile_dir: Path, user_pid: int | None) -> None:
    chrome_pids = profile_chrome_pids(profile_dir)
    if not chrome_pids or front_app_pid() not in chrome_pids:
        return
    lines = ['tell application "System Events"']
    for pid in chrome_pids:
        lines.append(
            "  try\n"
            f"    set frontmost of (first process whose unix id is {int(pid)}) to false\n"
            "  end try"
        )
    if user_pid and user_pid not in chrome_pids:
        lines.append(
            "  try\n"
            f"    set frontmost of (first process whose unix id is {int(user_pid)}) to true\n"
            "  end try"
        )
    lines.append("end tell")
    try:
        subprocess.run(
            ["osascript", "-e", "\n".join(lines)],
            check=False,
            capture_output=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def keep_behind(profile_dir: Path, user_pid: int | None, stop: threading.Event) -> None:
    remembered = user_pid
    while not stop.is_set():
        front = front_app_pid()
        chrome_pids = profile_chrome_pids(profile_dir)
        if front and front not in chrome_pids:
            remembered = front
        elif front and front in chrome_pids:
            demote_chrome(profile_dir, remembered)
        stop.wait(0.25)


def start_keep_behind(profile_dir: Path) -> threading.Event:
    stop = threading.Event()
    threading.Thread(
        target=keep_behind,
        args=(profile_dir, front_app_pid(), stop),
        daemon=True,
        name="chrome-sink",
    ).start()
    return stop
