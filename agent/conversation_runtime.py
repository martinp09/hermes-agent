from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from agent.runtime_backend import RuntimeBackend


@dataclass
class TurnSummary:
    final_response: Optional[str]
    messages: list
    api_calls: int
    interrupted: bool
    completed: bool
    system_prompt: str


class ConversationRuntime:
    """Backend-agnostic orchestration for one conversation turn."""

    def __init__(self, backend: RuntimeBackend, max_iterations: int) -> None:
        self.backend = backend
        self.max_iterations = max_iterations

    def run(
        self,
        *,
        messages: list,
        system_prompt: str,
        model: str,
        base_url: str,
        task_id: str,
        iteration_budget: Any,
        build_api_messages: Callable[[list, str], list],
        build_api_kwargs: Callable[[list], dict],
        parse_response: Callable[[Any], dict],
        estimate_tokens: Optional[Callable[[list], int]] = None,
        interrupt_check: Optional[Callable[[], bool]] = None,
    ) -> TurnSummary:
        api_call_count = 0
        final_response: Optional[str] = None
        interrupted = False
        prev_tool_names: list = []

        while api_call_count < self.max_iterations and iteration_budget.remaining > 0:
            if interrupt_check and interrupt_check():
                interrupted = True
                break

            turn_number = api_call_count + 1
            self.backend.on_turn_start(turn_number)
            if not iteration_budget.consume():
                break
            api_call_count = turn_number
            self.backend.on_iteration(api_call_count, prev_tool_names)

            api_messages = build_api_messages(messages, system_prompt)
            response = self.backend.make_api_call(build_api_kwargs(api_messages))
            parsed = parse_response(response)

            assistant_message = parsed.get("assistant_message")
            assistant_dict = parsed.get("assistant_dict")
            if assistant_dict:
                messages.append(assistant_dict)

            tool_calls = parsed.get("tool_calls") or []
            if not tool_calls:
                final_response = parsed.get("final_response")
                break

            tool_events = self.backend.execute_tools(assistant_message, messages, task_id) or []
            prev_tool_names = []
            for event in tool_events:
                name = str(event.get("name") or "")
                is_error = bool(event.get("is_error"))
                self.backend.on_tool_executed(name, is_error)
                if name:
                    prev_tool_names.append(
                        {"name": name, "result": event.get("result")}
                    )

            if interrupt_check and interrupt_check():
                interrupted = True
                break

            if estimate_tokens:
                estimated_tokens = estimate_tokens(messages)
                if self.backend.should_compress(estimated_tokens):
                    messages, system_prompt = self.backend.compress_context(
                        messages,
                        system_prompt,
                        model,
                        base_url,
                    )
                    self.backend.persist_session()

        return TurnSummary(
            final_response=final_response,
            messages=messages,
            api_calls=api_call_count,
            interrupted=interrupted,
            completed=final_response is not None and not interrupted,
            system_prompt=system_prompt,
        )
