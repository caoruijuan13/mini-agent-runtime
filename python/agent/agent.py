"""
Core Agent loop implementation.

The agent follows the standard ReAct-style loop:
1. Receive user message
2. Send conversation history to LLM (via Rust server)
3. If LLM returns tool_calls → execute tools → append results → goto 2
4. If LLM returns content → display to user → done
"""

import json
from typing import Callable

from .client import ServerClient
from .tools import ToolRegistry


class Agent:
    """
    A chat agent that communicates with the Rust server for LLM calls
    and executes tools locally.
    """

    MAX_ITERATIONS = 10  # Safety limit to prevent infinite loops

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:3000",
        tool_registry: ToolRegistry | None = None,
        system_prompt: str | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
        on_stream_chunk: Callable[[str], None] | None = None,
    ):
        self.client = ServerClient(server_url)
        self.tools = tool_registry or ToolRegistry()
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.messages: list[dict] = []
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.on_stream_chunk = on_stream_chunk

    def _default_system_prompt(self) -> str:
        return (
            "You are mini-agent, a helpful and friendly AI assistant. "
            "You have access to tools that you can use to help the user. "
            "When you need real-time information (weather, time, calculations), "
            "use the appropriate tools. Always explain what you're doing. "
            "Respond in the same language the user uses."
        )

    def reset(self):
        """Clear conversation history."""
        self.messages.clear()

    def chat(self, user_message: str, stream: bool = False) -> str:
        """
        Process a user message through the full agent loop.

        Args:
            user_message: The user's input text.
            stream: Whether to use streaming for the final response.

        Returns:
            The assistant's final text response.
        """
        # Add system prompt if this is the first message
        if not self.messages:
            self.messages.append({
                "role": "system",
                "content": self.system_prompt,
            })

        # Add user message
        self.messages.append({
            "role": "user",
            "content": user_message,
        })

        # Agent loop
        for iteration in range(self.MAX_ITERATIONS):
            # Call LLM via server
            response = self.client.chat(self.messages, stream=False)

            content = response.get("content")
            tool_calls = response.get("tool_calls")
            finish_reason = response.get("finish_reason", "stop")

            # If no tool calls, we have our final answer
            if not tool_calls or finish_reason == "stop":
                if content:
                    self.messages.append({
                        "role": "assistant",
                        "content": content,
                    })
                return content or "(No response)"

            # Process tool calls
            # Add assistant message with tool calls to history
            assistant_msg = {
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            }
            self.messages.append(assistant_msg)

            # Execute each tool call
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                # Notify callback
                if self.on_tool_call:
                    self.on_tool_call(func_name, func_args)

                # Execute tool
                result = self.tools.execute(func_name, func_args)

                # Notify callback
                if self.on_tool_result:
                    self.on_tool_result(func_name, result)

                # Add tool result to message history
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": func_name,
                    "content": result,
                })

        # If we exceeded max iterations
        return "⚠️ 达到了最大迭代次数限制，请尝试简化你的请求。"

    def chat_stream(self, user_message: str) -> str:
        """
        Process a user message with streaming output for the final response.
        Tool calls are still handled non-streaming for simplicity.

        Returns:
            The complete assistant response text.
        """
        # Add system prompt if first message
        if not self.messages:
            self.messages.append({
                "role": "system",
                "content": self.system_prompt,
            })

        self.messages.append({
            "role": "user",
            "content": user_message,
        })

        for iteration in range(self.MAX_ITERATIONS):
            # First try non-streaming to check for tool calls
            response = self.client.chat(self.messages, stream=False)

            tool_calls = response.get("tool_calls")
            finish_reason = response.get("finish_reason", "stop")

            if not tool_calls or finish_reason == "stop":
                # Final response — use streaming
                content = response.get("content", "")
                if content and self.on_stream_chunk:
                    # Simulate streaming character by character for mock mode
                    for char in content:
                        self.on_stream_chunk(char)
                    self.messages.append({
                        "role": "assistant",
                        "content": content,
                    })
                    return content

                if content:
                    self.messages.append({
                        "role": "assistant",
                        "content": content,
                    })
                return content or "(No response)"

            # Process tool calls (same as non-streaming)
            assistant_msg = {
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": tool_calls,
            }
            self.messages.append(assistant_msg)

            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                if self.on_tool_call:
                    self.on_tool_call(func_name, func_args)

                result = self.tools.execute(func_name, func_args)

                if self.on_tool_result:
                    self.on_tool_result(func_name, result)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": func_name,
                    "content": result,
                })

        return "⚠️ 达到了最大迭代次数限制，请尝试简化你的请求。"
