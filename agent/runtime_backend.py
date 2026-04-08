from __future__ import annotations

from typing import Any, Protocol


class RuntimeBackend(Protocol):
    def make_api_call(self, api_kwargs: dict) -> Any: ...

    def execute_tools(
        self,
        assistant_message: dict,
        messages: list,
        task_id: str,
    ) -> list: ...

    def should_compress(self, estimated_tokens: int) -> bool: ...

    def compress_context(
        self,
        messages: list,
        system_prompt: str,
        model: str,
        base_url: str,
    ) -> tuple: ...

    def persist_session(self) -> None: ...

    def on_turn_start(self, turn_number: int) -> None: ...

    def on_tool_executed(self, tool_name: str, is_error: bool) -> None: ...

    def on_iteration(self, iteration: int, prev_tool_names: list) -> None: ...
