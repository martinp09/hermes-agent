"""Tool execution hooks for ConversationRuntime."""
from __future__ import annotations

import logging
from typing import Optional, Protocol


logger = logging.getLogger(__name__)


class ToolHook(Protocol):
    def pre_tool_use(self, tool_name: str, arguments: str, call_id: str) -> Optional[str]:
        """Called before tool execution. Return modified arguments, or None to cancel."""

    def post_tool_use(self, tool_name: str, result: str, is_error: bool, call_id: str) -> str:
        """Called after tool execution. Return possibly modified result."""


class PreToolResult:
    def __init__(self, should_execute: bool, arguments: str, cancel_reason: str = ""):
        self.should_execute = should_execute
        self.arguments = arguments
        self.cancel_reason = cancel_reason


class HookRunner:
    def __init__(self):
        self._hooks: list[ToolHook] = []

    def register(self, hook: ToolHook) -> None:
        self._hooks.append(hook)

    def run_pre(self, tool_name: str, arguments: str, call_id: str) -> PreToolResult:
        """Run all pre-hooks. First cancel wins. Last argument modification wins."""
        current_args = arguments
        for hook in self._hooks:
            try:
                result = hook.pre_tool_use(tool_name, current_args, call_id)
            except Exception as exc:
                logger.warning("pre_tool_use hook %s failed: %s", hook.__class__.__name__, exc, exc_info=True)
                continue
            if result is None:
                return PreToolResult(
                    should_execute=False,
                    arguments=current_args,
                    cancel_reason=f"Cancelled by hook {hook.__class__.__name__}",
                )
            current_args = result
        return PreToolResult(should_execute=True, arguments=current_args)

    def run_post(self, tool_name: str, result: str, is_error: bool, call_id: str) -> str:
        """Run all post-hooks in order. Each can modify the result."""
        current = result
        for hook in self._hooks:
            try:
                current = hook.post_tool_use(tool_name, current, is_error, call_id)
            except Exception as exc:
                logger.warning("post_tool_use hook %s failed: %s", hook.__class__.__name__, exc, exc_info=True)
        return current
