"""Terminal styling and interactive prompts."""

from __future__ import annotations

import os
import sys


class _Style:
    """ANSI helpers; degrade cleanly when stdout is not a TTY."""

    def __init__(self) -> None:
        enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        self.enabled = enabled
        self.reset = "\033[0m" if enabled else ""
        self.bold = "\033[1m" if enabled else ""
        self.dim = "\033[2m" if enabled else ""
        self.cyan = "\033[36m" if enabled else ""
        self.green = "\033[32m" if enabled else ""
        self.yellow = "\033[33m" if enabled else ""
        self.red = "\033[31m" if enabled else ""
        self.magenta = "\033[35m" if enabled else ""

    def paint(self, text: str, *codes: str) -> str:
        if not self.enabled or not codes:
            return text
        return f"{''.join(codes)}{text}{self.reset}"


STYLE = _Style()


def print_banner(
    title: str = "Poseidon Installer",
    subtitle: str = "platform matrix · interactive setup",
) -> None:
    print(f"\n{STYLE.paint(title, STYLE.bold, STYLE.magenta)}")
    print(STYLE.paint(subtitle, STYLE.dim))
    print(STYLE.paint("─" * 36, STYLE.dim))


def print_section(title: str) -> None:
    print()
    print(STYLE.paint(title, STYLE.bold))
    print(STYLE.paint("─" * 36, STYLE.dim))


def _read_key() -> str:
    """Read a single keypress; returns 'up'/'down'/'enter'/'esc' or a character."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        first = sys.stdin.read(1)
        if first == "\x1b":
            rest = sys.stdin.read(2)
            if rest == "[A":
                return "up"
            if rest == "[B":
                return "down"
            return "esc"
        if first in {"\r", "\n"}:
            return "enter"
        if first in {"\x03"}:  # Ctrl-C
            raise KeyboardInterrupt
        return first
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _finish_select_summary(label: str, summary_value: str, lines: int) -> None:
    sys.stdout.write("\033[1A\033[2K")
    summary = (
        f"{STYLE.paint('✔', STYLE.green)} {STYLE.paint(label, STYLE.bold)} "
        f"{STYLE.paint(summary_value, STYLE.cyan)}"
    )
    sys.stdout.write(f"\033[{lines}A")
    sys.stdout.write("\033[J")
    sys.stdout.write(summary + "\n")
    sys.stdout.flush()


def _select_arrow(label: str, choices: list[tuple[str, str]], default: str) -> str:
    index = next((i for i, (value, _) in enumerate(choices) if value == default), 0)
    hint = STYLE.paint("↑/↓ move · enter confirm · q quit", STYLE.dim)

    def render(*, first: bool) -> None:
        if not first:
            sys.stdout.write(f"\033[{len(choices) + 2}A")
        sys.stdout.write(f"{STYLE.paint('?', STYLE.cyan, STYLE.bold)} {STYLE.paint(label, STYLE.bold)}\n")
        for i, (_value, title) in enumerate(choices):
            if i == index:
                marker = STYLE.paint("❯", STYLE.cyan, STYLE.bold)
                text = STYLE.paint(title, STYLE.cyan, STYLE.bold)
            else:
                marker = " "
                text = title
            sys.stdout.write(f"  {marker} {text}\n")
        sys.stdout.write(f"  {hint}\n")
        sys.stdout.flush()

    render(first=True)
    while True:
        key = _read_key()
        if key == "up":
            index = (index - 1) % len(choices)
            render(first=False)
        elif key == "down":
            index = (index + 1) % len(choices)
            render(first=False)
        elif key == "enter":
            selected = choices[index]
            _finish_select_summary(label, selected[1], len(choices) + 1)
            return selected[0]
        elif key in {"q", "esc"}:
            raise SystemExit(STYLE.paint("Aborted.", STYLE.dim))


def _select_numbered(label: str, choices: list[tuple[str, str]], default: str) -> str:
    print(f"\n{STYLE.paint('?', STYLE.cyan, STYLE.bold)} {STYLE.paint(label, STYLE.bold)}")
    for i, (value, title) in enumerate(choices, start=1):
        suffix = STYLE.paint(" (default)", STYLE.dim) if value == default else ""
        print(f"  {STYLE.paint(str(i), STYLE.dim)}. {title}{suffix}")
    raw = input(f"{STYLE.paint('❯', STYLE.cyan)} ").strip()
    if not raw:
        return default
    if raw.isdigit() and 1 <= int(raw) <= len(choices):
        return choices[int(raw) - 1][0]
    values = {value for value, _title in choices}
    if raw in values:
        return raw
    raise SystemExit(f"Invalid choice: {raw}")


def select_choice(label: str, choices: list[tuple[str, str]], default: str) -> str:
    if not choices:
        raise SystemExit("No choices available.")
    values = {value for value, _title in choices}
    if default not in values:
        default = choices[0][0]
    use_arrow = sys.stdin.isatty() and sys.stdout.isatty() and sys.platform != "win32"
    if use_arrow:
        try:
            return _select_arrow(label, choices, default)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except (ImportError, OSError):
            pass
    return _select_numbered(label, choices, default)


def _select_multi_arrow(
    label: str,
    choices: list[tuple[str, str]],
    defaults: set[str],
) -> list[str]:
    index = 0
    selected = {value for value, _title in choices if value in defaults}
    hint = STYLE.paint("↑/↓ move · space toggle · a all · enter confirm · q quit", STYLE.dim)

    def render(*, first: bool) -> None:
        if not first:
            sys.stdout.write(f"\033[{len(choices) + 2}A")
        sys.stdout.write(f"{STYLE.paint('?', STYLE.cyan, STYLE.bold)} {STYLE.paint(label, STYLE.bold)}\n")
        for i, (value, title) in enumerate(choices):
            checked = value in selected
            box = STYLE.paint("◉", STYLE.cyan) if checked else STYLE.paint("◯", STYLE.dim)
            if i == index:
                marker = STYLE.paint("❯", STYLE.cyan, STYLE.bold)
                text = STYLE.paint(title, STYLE.cyan, STYLE.bold)
            else:
                marker = " "
                text = title
            sys.stdout.write(f"  {marker} {box} {text}\n")
        sys.stdout.write(f"  {hint}\n")
        sys.stdout.flush()

    render(first=True)
    while True:
        key = _read_key()
        if key == "up":
            index = (index - 1) % len(choices)
            render(first=False)
        elif key == "down":
            index = (index + 1) % len(choices)
            render(first=False)
        elif key == " ":
            value = choices[index][0]
            if value in selected:
                selected.remove(value)
            else:
                selected.add(value)
            render(first=False)
        elif key == "a":
            values = {value for value, _title in choices}
            selected = set() if selected == values else values
            render(first=False)
        elif key == "enter":
            if not selected:
                continue
            ordered = [value for value, _title in choices if value in selected]
            titles = [title for value, title in choices if value in selected]
            summary = "All" if len(ordered) == len(choices) else ", ".join(titles)
            _finish_select_summary(label, summary, len(choices) + 1)
            return ordered
        elif key in {"q", "esc"}:
            raise SystemExit(STYLE.paint("Aborted.", STYLE.dim))


def _select_multi_numbered(
    label: str,
    choices: list[tuple[str, str]],
    defaults: set[str],
) -> list[str]:
    default_values = [value for value, _title in choices if value in defaults]
    print(f"\n{STYLE.paint('?', STYLE.cyan, STYLE.bold)} {STYLE.paint(label, STYLE.bold)}")
    print(STYLE.paint("  comma-separated numbers or 'all' (required)", STYLE.dim))
    for i, (value, title) in enumerate(choices, start=1):
        mark = STYLE.paint("*", STYLE.cyan) if value in default_values else " "
        print(f"  {STYLE.paint(str(i), STYLE.dim)}. [{mark}] {title}")
    raw = input(f"{STYLE.paint('❯', STYLE.cyan)} ").strip().lower()
    if not raw:
        if default_values:
            return default_values
        raise SystemExit("Select at least one option.")
    if raw == "all":
        return [value for value, _title in choices]
    picked: list[str] = []
    for token in raw.replace(" ", "").split(","):
        if not token:
            continue
        if token.isdigit() and 1 <= int(token) <= len(choices):
            value = choices[int(token) - 1][0]
            if value not in picked:
                picked.append(value)
            continue
        values = {value for value, _title in choices}
        if token in values and token not in picked:
            picked.append(token)
            continue
        raise SystemExit(f"Invalid choice: {token}")
    if not picked:
        raise SystemExit("Select at least one option.")
    return picked


def select_multiple(
    label: str,
    choices: list[tuple[str, str]],
    defaults: set[str] | None = None,
) -> list[str]:
    if not choices:
        raise SystemExit("No choices available.")
    default_set = set(defaults) if defaults is not None else set()
    use_arrow = sys.stdin.isatty() and sys.stdout.isatty() and sys.platform != "win32"
    if use_arrow:
        try:
            return _select_multi_arrow(label, choices, default_set)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except (ImportError, OSError):
            pass
    return _select_multi_numbered(label, choices, default_set)
