"""Small, explicit Agent Runtime execution kernel.

The runtime owns protocol transitions and tool execution. It does not choose a
persona, render a terminal UI, or decide how a product should prompt a model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .client import ServerClient
from .tools import ToolRegistry


class RunStatus(str, Enum):
    """Terminal state of one runtime execution."""

    COMPLETED = "completed"
    MAX_STEPS = "max_steps"
    FAILED = "failed"


@dataclass(frozen=True)
class RuntimeConfig:
    """Execution budgets owned by the runtime, not by an Agent persona."""

    max_steps: int = 10

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")


@dataclass(frozen=True)
class RuntimeEvent:
    """An observational event emitted at a runtime boundary."""

    kind: str
    step: int
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    """Structured result for one run, including its resulting message history."""

    status: RunStatus
    messages: list[dict[str, Any]]
    steps: int
    content: str | None = None
    error: str | None = None


class AgentRuntime:
    """Execute the model/tool protocol without product-specific behavior."""

    def __init__(
        self,
        client: ServerClient,
        tools: ToolRegistry,
        config: RuntimeConfig | None = None,
        on_event: Callable[[RuntimeEvent], None] | None = None,
    ):
        self.client = client
        self.tools = tools
        self.config = config or RuntimeConfig()
        self.on_event = on_event

    def run(self, messages: list[dict[str, Any]]) -> RunResult:
        """Run until a final model response, failure, or the step budget ends."""
        history = [dict(message) for message in messages]

        for step in range(1, self.config.max_steps + 1):
            self._emit(RuntimeEvent("model_requested", step, {"message_count": len(history)}))
            try:
                response = self.client.chat(history, stream=False)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                self._emit(RuntimeEvent("run_failed", step, {"error": error}))
                return RunResult(RunStatus.FAILED, history, step, error=error)
            if not isinstance(response, dict):
                error = "model protocol error: response must be an object"
                self._emit(RuntimeEvent("run_failed", step, {"error": error}))
                return RunResult(RunStatus.FAILED, history, step, error=error)

            content = response.get("content")
            raw_tool_calls = response.get("tool_calls")
            if raw_tool_calls is None:
                tool_calls = []
            elif isinstance(raw_tool_calls, list):
                tool_calls = raw_tool_calls
            else:
                error = "model protocol error: tool_calls must be a list"
                self._emit(RuntimeEvent("run_failed", step, {"error": error}))
                return RunResult(RunStatus.FAILED, history, step, error=error)
            finish_reason = response.get("finish_reason", "stop")
            self._emit(RuntimeEvent(
                "model_responded",
                step,
                {"finish_reason": finish_reason, "tool_call_count": len(tool_calls)},
            ))

            if not tool_calls:
                if content is not None:
                    history.append({"role": "assistant", "content": content})
                self._emit(RuntimeEvent("run_completed", step, {"finish_reason": finish_reason}))
                return RunResult(RunStatus.COMPLETED, history, step, content=content)

            history.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    result = "Error: tool call must be an object"
                    history.append({
                        "role": "tool",
                        "tool_call_id": "",
                        "name": "",
                        "content": result,
                    })
                    self._emit(RuntimeEvent("tool_completed", step, {"name": "", "content": result}))
                    continue
                tool_id = tool_call.get("id", "")
                function = tool_call.get("function") or {}
                if not isinstance(function, dict):
                    function = {}
                name = function.get("name", "")
                arguments_text = function.get("arguments", "{}")
                arguments, parse_error = self._parse_arguments(arguments_text)
                self._emit(RuntimeEvent(
                    "tool_requested",
                    step,
                    {"tool_call_id": tool_id, "name": name, "arguments": arguments_text},
                ))

                result = parse_error or self.tools.execute(name, arguments)
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "name": name,
                    "content": result,
                })
                self._emit(RuntimeEvent(
                    "tool_completed",
                    step,
                    {"tool_call_id": tool_id, "name": name, "content": result},
                ))

        error = f"runtime exceeded max_steps={self.config.max_steps}"
        self._emit(RuntimeEvent("run_max_steps", self.config.max_steps, {"error": error}))
        return RunResult(RunStatus.MAX_STEPS, history, self.config.max_steps, error=error)

    @staticmethod
    def _parse_arguments(arguments: Any) -> tuple[dict[str, Any], str | None]:
        if isinstance(arguments, dict):
            return arguments, None
        if not isinstance(arguments, str):
            return {}, "Error: tool arguments must be a JSON object"
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as exc:
            return {}, f"Error: invalid JSON tool arguments: {exc.msg}"
        if not isinstance(parsed, dict):
            return {}, "Error: tool arguments must be a JSON object"
        return parsed, None

    def _emit(self, event: RuntimeEvent) -> None:
        if self.on_event is None:
            return
        try:
            self.on_event(event)
        except Exception:
            # Observers must not change run semantics.
            return
