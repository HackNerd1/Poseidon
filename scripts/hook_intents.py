#!/usr/bin/env python3
"""Render platform-specific hook configs from canonical hook intents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Union


YamlValue = Union[dict[str, Any], list[Any], str, int, bool, None]

INTENTS_DIR = Path("hooks") / "intents"
SEMANTIC_EVENT_ORDER = {
    "turn_stop": 10,
    "question_request": 20,
    "permission_request": 30,
    "idle_prompt": 40,
}
SUPPORTED_PLATFORMS = {"claude", "codex"}
FLAG_BY_FIELD = {
    "no_wait": "--no-wait",
    "quiet": "--quiet",
    "best_effort": "--best-effort",
}


def discover_intent_files(plugin_dir: Path) -> list[Path]:
    """Return canonical hook intent files for a plugin."""

    intents_dir = plugin_dir / INTENTS_DIR
    if not intents_dir.exists():
        return []
    return sorted(intents_dir.glob("*.yaml"))


def parse_intent_file(path: Path) -> dict[str, Any]:
    """Parse one controlled-subset YAML intent file."""

    parsed = parse_controlled_yaml(path.read_text(encoding="utf-8"), source=path)
    if not isinstance(parsed, dict):
        raise ValueError(f"{path}: intent file must contain a mapping")
    return parsed


def render_platform_hooks(
    plugin_dir: Path,
    platform: str,
    context: dict[str, str],
) -> dict[str, Any] | None:
    """Render hooks JSON for a platform, or None when the plugin has no intents."""

    platform = platform.lower()
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported hook platform: {platform}")

    intent_files = discover_intent_files(plugin_dir)
    if not intent_files:
        return None

    intents = [parse_intent_file(path) for path in intent_files]
    intents.sort(key=_intent_sort_key)

    hooks: dict[str, list[dict[str, Any]]] = {}
    for intent in intents:
        rendered = _render_intent(intent, platform, context)
        if rendered is None:
            continue
        event, group = rendered
        hooks.setdefault(event, []).append(group)

    return {"hooks": hooks}


def parse_controlled_yaml(text: str, source: Path | str = "<string>") -> YamlValue:
    """Parse the small YAML subset used by hook intents.

    Supported syntax is intentionally narrow: two-space indentation, mappings,
    lists, comments, strings, booleans, integers, and nulls. This keeps intent
    files human-readable without adding a runtime dependency on PyYAML.
    """

    lines = _tokenize_yaml(text, source)
    if not lines:
        return {}
    value, index = _parse_block(lines, 0, lines[0][0], source)
    if index != len(lines):
        line_no = lines[index][1]
        raise ValueError(f"{source}:{line_no}: unexpected trailing content")
    return value


def _tokenize_yaml(text: str, source: Path | str) -> list[tuple[int, int, str]]:
    tokens: list[tuple[int, int, str]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        if "\t" in raw_line:
            raise ValueError(f"{source}:{line_no}: tabs are not supported")
        stripped = _strip_comment(raw_line).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if indent % 2:
            raise ValueError(f"{source}:{line_no}: indentation must use multiples of two spaces")
        tokens.append((indent, line_no, stripped[indent:]))
    return tokens


def _strip_comment(line: str) -> str:
    quote: str | None = None
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            if char == "\\" and quote == '"' and index + 1 < len(line):
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "#":
            return line[:index]
        index += 1
    return line


def _parse_block(
    lines: list[tuple[int, int, str]],
    index: int,
    indent: int,
    source: Path | str,
) -> tuple[YamlValue, int]:
    if index >= len(lines):
        return {}, index

    actual_indent, line_no, content = lines[index]
    if actual_indent != indent:
        raise ValueError(f"{source}:{line_no}: expected indentation level {indent}")
    if content.startswith("- "):
        return _parse_list(lines, index, indent, source)
    return _parse_mapping(lines, index, indent, source)


def _parse_mapping(
    lines: list[tuple[int, int, str]],
    index: int,
    indent: int,
    source: Path | str,
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        actual_indent, line_no, content = lines[index]
        if actual_indent < indent:
            break
        if actual_indent > indent:
            raise ValueError(f"{source}:{line_no}: unexpected indentation")
        if content.startswith("- "):
            break

        key, raw_value = _split_mapping_item(content, source, line_no)
        if not key:
            raise ValueError(f"{source}:{line_no}: empty mapping key")
        if raw_value == "":
            next_index = index + 1
            if next_index >= len(lines) or lines[next_index][0] <= indent:
                result[key] = {}
                index = next_index
            else:
                result[key], index = _parse_block(lines, next_index, lines[next_index][0], source)
        else:
            result[key] = _parse_scalar(raw_value, source, line_no)
            index += 1
    return result, index


def _parse_list(
    lines: list[tuple[int, int, str]],
    index: int,
    indent: int,
    source: Path | str,
) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        actual_indent, line_no, content = lines[index]
        if actual_indent < indent:
            break
        if actual_indent > indent:
            raise ValueError(f"{source}:{line_no}: unexpected indentation")
        if not content.startswith("- "):
            break

        item = content[2:].strip()
        if item == "":
            next_index = index + 1
            if next_index >= len(lines) or lines[next_index][0] <= indent:
                result.append({})
                index = next_index
            else:
                value, index = _parse_block(lines, next_index, lines[next_index][0], source)
                result.append(value)
        elif ":" in item and not _is_quoted(item):
            key, raw_value = _split_mapping_item(item, source, line_no)
            mapping: dict[str, Any] = {}
            if raw_value == "":
                next_index = index + 1
                if next_index >= len(lines) or lines[next_index][0] <= indent:
                    mapping[key] = {}
                    index = next_index
                else:
                    mapping[key], index = _parse_block(lines, next_index, lines[next_index][0], source)
            else:
                mapping[key] = _parse_scalar(raw_value, source, line_no)
                index += 1
            result.append(mapping)
        else:
            result.append(_parse_scalar(item, source, line_no))
            index += 1
    return result, index


def _split_mapping_item(content: str, source: Path | str, line_no: int) -> tuple[str, str]:
    quote: str | None = None
    for index, char in enumerate(content):
        if quote:
            if char == "\\" and quote == '"' and index + 1 < len(content):
                continue
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == ":":
            return content[:index].strip(), content[index + 1 :].strip()
    raise ValueError(f"{source}:{line_no}: expected mapping item")


def _parse_scalar(value: str, source: Path | str, line_no: int) -> str | int | bool | None:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if re.fullmatch(r"-?[0-9]+", value):
        return int(value)
    if _is_quoted(value):
        return _unquote(value, source, line_no)
    return value


def _is_quoted(value: str) -> bool:
    return len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}


def _unquote(value: str, source: Path | str, line_no: int) -> str:
    quote = value[0]
    inner = value[1:-1]
    if quote == "'":
        return inner.replace("''", "'")

    result: list[str] = []
    index = 0
    escapes = {
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }
    while index < len(inner):
        char = inner[index]
        if char != "\\":
            result.append(char)
            index += 1
            continue
        index += 1
        if index >= len(inner):
            raise ValueError(f"{source}:{line_no}: dangling escape in quoted string")
        escaped = inner[index]
        if escaped not in escapes:
            raise ValueError(f"{source}:{line_no}: unsupported escape sequence \\{escaped}")
        result.append(escapes[escaped])
        index += 1
    return "".join(result)


def _intent_sort_key(intent: dict[str, Any]) -> tuple[int, str]:
    semantic_event = str(intent.get("semantic_event") or "")
    intent_id = str(intent.get("id") or "")
    return SEMANTIC_EVENT_ORDER.get(semantic_event, 1000), intent_id


def _render_intent(
    intent: dict[str, Any],
    platform: str,
    context: dict[str, str],
) -> tuple[str, dict[str, Any]] | None:
    handler = _required_mapping(intent, "handler")
    platforms = _required_mapping(intent, "platforms")
    platform_config = platforms.get(platform)
    if platform_config is None:
        return None
    if not isinstance(platform_config, dict):
        raise ValueError(f"{_intent_label(intent)}: platforms.{platform} must be a mapping")

    event = _required_string(platform_config, "event", intent)
    hook = _render_command_hook(intent, handler, platform_config, platform, context)
    group: dict[str, Any] = {}
    matcher = platform_config.get("matcher")
    if matcher is not None:
        group["matcher"] = str(matcher)
    group["hooks"] = [hook]
    return event, group


def _render_command_hook(
    intent: dict[str, Any],
    handler: dict[str, Any],
    platform_config: dict[str, Any],
    platform: str,
    context: dict[str, str],
) -> dict[str, Any]:
    handler_type = _required_string(handler, "type", intent)
    if handler_type != "command":
        raise ValueError(f"{_intent_label(intent)}: only command handlers are supported")

    stdout_policy = str(platform_config.get("stdout_policy") or "")
    if platform == "codex" and stdout_policy == "empty":
        if not _effective_bool(handler, platform_config, platform, "quiet"):
            raise ValueError(f"{_intent_label(intent)}: Codex empty stdout hooks require quiet: true")
        if not _effective_bool(handler, platform_config, platform, "best_effort"):
            raise ValueError(f"{_intent_label(intent)}: Codex empty stdout hooks require best_effort: true")

    script = _required_string(handler, "script", intent)
    hook: dict[str, Any] = {
        "type": "command",
        "command": _render_command(intent, handler, platform_config, platform, context, script),
    }

    windows_root_var = platform_config.get("windows_root_var")
    if platform == "codex" and windows_root_var:
        hook["commandWindows"] = _render_command(
            intent,
            handler,
            platform_config,
            platform,
            context,
            script,
            windows=True,
        )

    timeout = platform_config.get("timeout")
    if timeout is not None:
        if not isinstance(timeout, int):
            raise ValueError(f"{_intent_label(intent)}: timeout must be an integer")
        hook["timeout"] = timeout

    status_message = platform_config.get("status_message")
    if status_message is not None:
        hook["statusMessage"] = str(status_message)

    if platform_config.get("async") is not None:
        hook["async"] = bool(platform_config["async"])

    return hook


def _render_command(
    intent: dict[str, Any],
    handler: dict[str, Any],
    platform_config: dict[str, Any],
    platform: str,
    context: dict[str, str],
    script: str,
    windows: bool = False,
) -> str:
    root_var_field = "windows_root_var" if windows else "root_var"
    root_var = _required_string(platform_config, root_var_field, intent)
    root = _context_value(context, root_var)
    script_path = _join_script_path(root, script, windows)
    executable = _executable(platform_config, platform, windows)

    args = [
        executable,
        script_path,
        _platform_text(handler, "title", platform, intent),
        _platform_text(handler, "message", platform, intent),
    ]
    for field, flag in FLAG_BY_FIELD.items():
        if _effective_bool(handler, platform_config, platform, field):
            args.append(flag)
    return " ".join(_format_command_arg(arg, index) for index, arg in enumerate(args))


def _executable(platform_config: dict[str, Any], platform: str, windows: bool) -> str:
    if windows:
        return str(platform_config.get("windows_executable") or "python")
    return str(platform_config.get("executable") or ("python3" if platform == "codex" else "python"))


def _join_script_path(root: str, script: str, windows: bool) -> str:
    if windows:
        return root.rstrip("\\/") + "\\" + script.replace("/", "\\")
    return root.rstrip("/") + "/" + script.replace("\\", "/")


def _quote_arg(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def _format_command_arg(value: str, index: int) -> str:
    if index == 0 or value.startswith("--"):
        return value
    return _quote_arg(value)


def _platform_text(
    handler: dict[str, Any],
    field: str,
    platform: str,
    intent: dict[str, Any],
) -> str:
    value = handler.get(field)
    if isinstance(value, dict):
        if platform in value:
            return str(value[platform])
        if "default" in value:
            return str(value["default"])
    if isinstance(value, str):
        return value
    raise ValueError(f"{_intent_label(intent)}: handler.{field} missing value for {platform}")


def _effective_bool(
    handler: dict[str, Any],
    platform_config: dict[str, Any],
    platform: str,
    field: str,
) -> bool:
    if field in platform_config:
        return bool(platform_config[field])
    value = handler.get(field)
    if isinstance(value, dict):
        if platform in value:
            return bool(value[platform])
        if "default" in value:
            return bool(value["default"])
        return False
    return bool(value)


def _context_value(context: dict[str, str], name: str) -> str:
    if name in context:
        return str(context[name])
    lower_name = name.lower()
    if lower_name in context:
        return str(context[lower_name])
    placeholders = context.get("placeholders")  # type: ignore[assignment]
    if isinstance(placeholders, dict) and name in placeholders:
        return str(placeholders[name])
    raise KeyError(f"missing hook render context value: {name}")


def _required_mapping(mapping: dict[str, Any], field: str) -> dict[str, Any]:
    value = mapping.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"{_intent_label(mapping)}: {field} must be a mapping")
    return value


def _required_string(mapping: dict[str, Any], field: str, intent: dict[str, Any]) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{_intent_label(intent)}: {field} must be a non-empty string")
    return value


def _intent_label(intent: dict[str, Any]) -> str:
    intent_id = intent.get("id")
    return f"intent {intent_id}" if intent_id else "hook intent"
