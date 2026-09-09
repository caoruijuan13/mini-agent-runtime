"""Thin application adapter around :mod:`agent.runtime`.

The runtime owns execution semantics. This class only owns a conversation
buffer and the optional application-level system message.
"""

from __future__ import annotations

from typing import Any, Callable

from .client import ServerClient
from .runtime import AgentRuntime, RunResult, RunStatus, RuntimeConfig, RuntimeEvent
from .tools import ToolRegistry


class Agent:
    """Small chat facade for applications that need a conversation buffer."""

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:3000",
        tool_registry: ToolRegistry | None = None,
        system_prompt: str | None = None,
        max_steps: int = 10,
        on_event: Callable[[RuntimeEvent], None] | None = None,
    ):
        self.client = ServerClient(server_url)
        self.tools = tool_registry or ToolRegistry()
        self.system_prompt = system_prompt
        self.messages: list[dict[str, Any]] = []
        self.runtime = AgentRuntime(
            self.client,
            self.tools,
            RuntimeConfig(max_steps=max_steps),
            on_event=on_event,
        )

    def reset(self) -> None:
        """Discard the application conversation buffer."""
        self.messages.clear()

    def run(self, user_message: str) -> RunResult:
        """Append one user message and return the structured runtime result."""
        history = [dict(message) for message in self.messages]
        if self.system_prompt is not None and not history:
            history.append({"role": "system", "content": self.system_prompt})
        history.append({"role": "user", "content": user_message})
        result = self.runtime.run(history)
        self.messages = result.messages
        return result

    def chat(self, user_message: str) -> str:
        """Convenience method that returns only final text."""
        result = self.run(user_message)
        if result.status is RunStatus.COMPLETED:
            return result.content or "(No response)"
        if result.status is RunStatus.MAX_STEPS:
            return "⚠️ 运行时达到最大步骤数限制，请尝试简化你的请求。"
        return f"⚠️ 运行时执行失败: {result.error or 'unknown error'}"
