"""Shared helpers for Poseidon install/uninstall CLIs."""

from shared.common import (
    SCOPES,
    SUPPORTED_SCOPES,
    encode_platform_arg,
    encode_plugin_arg,
    effective_scope,
    interactive_fill,
    repo_root,
    target_platforms,
    validate_scope,
    wants_interactive,
)
from shared.operations import (
    Operation,
    describe_operation,
    display_path,
    operation_platform,
    print_done,
    print_plan,
    summarize_command_output,
)
from shared.ui import STYLE, print_banner, print_section, select_choice, select_multiple

__all__ = [
    "SCOPES",
    "STYLE",
    "SUPPORTED_SCOPES",
    "Operation",
    "describe_operation",
    "display_path",
    "encode_platform_arg",
    "encode_plugin_arg",
    "effective_scope",
    "interactive_fill",
    "operation_platform",
    "print_banner",
    "print_done",
    "print_plan",
    "print_section",
    "repo_root",
    "select_choice",
    "select_multiple",
    "summarize_command_output",
    "target_platforms",
    "validate_scope",
    "wants_interactive",
]
