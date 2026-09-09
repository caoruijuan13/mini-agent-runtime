"""
Integration tests for the mini-agent system.

These tests verify the full agent loop works correctly,
including server communication and tool execution.
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from agent.tools import create_default_registry
from agent.agent import Agent
from agent.runtime import RunStatus

TEST_SERVER_URL = os.environ.get("TEST_SERVER_URL", "http://127.0.0.1:3000")


class TestAgentWithoutServer:
    """
    Test the agent logic without requiring a running server.
    These tests mock the server client.
    """

    def _make_agent(self) -> Agent:
        """Create an agent with a mock client."""
        agent = Agent(
            server_url="http://localhost:9999",  # won't connect
            tool_registry=create_default_registry(),
        )
        return agent

    def test_agent_creation(self):
        agent = self._make_agent()
        assert agent.tools is not None
        assert len(agent.tools.names) >= 5
        assert agent.messages == []

    def test_agent_reset(self):
        agent = self._make_agent()
        agent.messages.append({"role": "user", "content": "test"})
        assert len(agent.messages) == 1
        agent.reset()
        assert len(agent.messages) == 0

    def test_system_prompt_added(self):
        """Verify prompting is an explicit application concern."""
        agent = Agent(
            server_url="http://localhost:9999",
            tool_registry=create_default_registry(),
            system_prompt="Use tools only when needed.",
        )
        assert agent.system_prompt == "Use tools only when needed."

    def test_tool_execution_weather(self):
        """Test that weather tool executes correctly."""
        agent = self._make_agent()
        result = agent.tools.execute("get_weather", {"city": "北京"})
        assert "北京" in result
        assert "天气" in result

    def test_tool_execution_calculate(self):
        """Test that calculate tool executes correctly."""
        agent = self._make_agent()
        result = agent.tools.execute("calculate", {"expression": "2 ** 10"})
        assert "1024" in result

    def test_tool_execution_time(self):
        """Test that time tool executes correctly."""
        agent = self._make_agent()
        result = agent.tools.execute("get_current_time", {"timezone": "UTC"})
        assert "UTC" in result

    def test_tool_execution_translate(self):
        """Test that translate tool executes correctly."""
        agent = self._make_agent()
        result = agent.tools.execute("translate", {"text": "你好", "target_language": "English"})
        assert "Hello" in result

    def test_tool_execution_search(self):
        """Test that search tool executes correctly."""
        agent = self._make_agent()
        result = agent.tools.execute("search_knowledge", {"query": "Rust"})
        assert "Rust" in result

    def test_unknown_tool_returns_error(self):
        """Test that unknown tools return an error message."""
        agent = self._make_agent()
        result = agent.tools.execute("nonexistent", {})
        assert "Error" in result or "Unknown" in result

    def test_runtime_events_are_observational(self):
        """Runtime events replace tool-specific callback plumbing."""
        events = []
        agent = Agent(
            server_url="http://localhost:9999",
            tool_registry=create_default_registry(),
            on_event=events.append,
        )

        assert len(agent.tools.names) >= 5
        assert events == []


class TestMockAgentLoop:
    """
    Test the agent loop with a mocked server client.
    """

    def _make_agent_with_mock_client(self) -> Agent:
        """Create agent with mocked server responses."""
        agent = Agent(
            server_url="http://localhost:9999",
            tool_registry=create_default_registry(),
        )

        # Mock the client's chat method
        call_count = [0]

        def mock_chat(messages, stream=False):
            call_count[0] += 1
            last_msg = messages[-1]

            # If last message is a tool result, return final answer
            if last_msg.get("role") == "tool":
                return {
                    "content": f"根据工具返回的结果，答案是: {last_msg['content']}",
                    "tool_calls": None,
                    "finish_reason": "stop",
                }

            # First call: return a tool call
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": f"call_{call_count[0]}",
                        "type": "function",
                        "function": {
                            "name": "calculate",
                            "arguments": json.dumps({"expression": "2 + 2"}),
                        },
                    }
                ],
                "finish_reason": "tool_calls",
            }

        agent.client.chat = mock_chat
        return agent

    def test_agent_loop_with_tool_call(self):
        """Test that agent correctly handles tool calls and returns final answer."""
        agent = self._make_agent_with_mock_client()
        result = agent.chat("计算 2 + 2")

        # Should have gone through tool call and returned final answer
        assert "4" in result or "计算" in result
        assert len(agent.messages) > 2  # system + user + assistant(tool_call) + tool + assistant(final)

    def test_agent_resets_cleanly(self):
        """Test that agent can be reset and reused."""
        agent = self._make_agent_with_mock_client()
        agent.chat("test 1")
        agent.reset()
        assert len(agent.messages) == 0

    def test_max_iterations_safety(self):
        """Test that agent stops after max iterations."""
        agent = Agent(
            server_url="http://localhost:9999",
            tool_registry=create_default_registry(),
        )
        agent.runtime.config = agent.runtime.config.__class__(max_steps=2)

        # Mock client that always returns tool calls (infinite loop scenario)
        def mock_chat(messages, stream=False):
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_loop",
                        "type": "function",
                        "function": {
                            "name": "calculate",
                            "arguments": json.dumps({"expression": "1 + 1"}),
                        },
                    }
                ],
                "finish_reason": "tool_calls",
            }

        agent.client.chat = mock_chat
        result = agent.chat("infinite loop test")
        assert "步骤" in result or "限制" in result

    def test_structured_run_result(self):
        agent = self._make_agent_with_mock_client()
        result = agent.run("计算 2 + 2")
        assert result.status is RunStatus.COMPLETED
        assert result.steps == 2
        assert result.content is not None


class TestServerIntegration:
    """
    Integration tests that require the Rust server to be running.
    These are skipped if the server is not available.
    """

    @pytest.fixture(autouse=True)
    def check_server(self):
        """Skip tests if server is not running."""
        from agent.client import ServerClient
        client = ServerClient(TEST_SERVER_URL)
        if not client.is_server_running():
            pytest.skip("Rust server not running on localhost:3000")

    def test_health_endpoint(self):
        from agent.client import ServerClient
        client = ServerClient(TEST_SERVER_URL)
        health = client.health()
        assert health["status"] == "ok"
        assert "version" in health

    def test_tools_endpoint(self):
        from agent.client import ServerClient
        client = ServerClient(TEST_SERVER_URL)
        tools = client.list_tools()
        assert len(tools) >= 5

    def test_chat_endpoint(self):
        from agent.client import ServerClient
        client = ServerClient(TEST_SERVER_URL)
        response = client.chat([{"role": "user", "content": "你好"}])
        assert "content" in response or "tool_calls" in response

    def test_full_agent_loop(self):
        """Test the complete agent loop with real server."""
        agent = Agent(
            server_url=TEST_SERVER_URL,
            tool_registry=create_default_registry(),
        )
        result = agent.chat("你好")
        assert result is not None
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
