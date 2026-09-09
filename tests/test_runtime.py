"""Focused tests for the Agent Runtime state and protocol boundaries."""

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from agent.runtime import AgentRuntime, RunStatus, RuntimeConfig
from agent.tools import create_default_registry


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)

    def chat(self, messages, stream=False):
        return next(self.responses)


def tool_call(arguments):
    return {
        "id": "call_1",
        "type": "function",
        "function": {
            "name": "calculate",
            "arguments": json.dumps(arguments),
        },
    }


def test_runtime_completes_tool_then_text():
    events = []
    runtime = AgentRuntime(
        FakeClient([
            {"content": None, "tool_calls": [tool_call({"expression": "2 + 2"})], "finish_reason": "tool_calls"},
            {"content": "4", "tool_calls": None, "finish_reason": "stop"},
        ]),
        create_default_registry(),
        on_event=events.append,
    )

    result = runtime.run([{"role": "user", "content": "计算"}])

    assert result.status is RunStatus.COMPLETED
    assert result.steps == 2
    assert result.content == "4"
    assert [event.kind for event in events] == [
        "model_requested", "model_responded", "tool_requested", "tool_completed",
        "model_requested", "model_responded", "run_completed",
    ]


def test_runtime_rejects_invalid_arguments_without_empty_fallback():
    runtime = AgentRuntime(
        FakeClient([
            {
                "content": None,
                "tool_calls": [{
                    "id": "call_bad",
                    "type": "function",
                    "function": {"name": "calculate", "arguments": "{"},
                }],
                "finish_reason": "tool_calls",
            },
            {"content": "recovered", "tool_calls": None, "finish_reason": "stop"},
        ]),
        create_default_registry(),
    )

    result = runtime.run([{"role": "user", "content": "test"}])

    assert result.status is RunStatus.COMPLETED
    tool_result = result.messages[-2]
    assert tool_result["role"] == "tool"
    assert "invalid JSON" in tool_result["content"]


def test_runtime_has_explicit_max_steps_terminal_state():
    response = {"content": None, "tool_calls": [tool_call({"expression": "1 + 1"})], "finish_reason": "tool_calls"}
    runtime = AgentRuntime(
        FakeClient([response, response]),
        create_default_registry(),
        RuntimeConfig(max_steps=2),
    )

    result = runtime.run([{"role": "user", "content": "loop"}])

    assert result.status is RunStatus.MAX_STEPS
    assert result.steps == 2
    assert result.error == "runtime exceeded max_steps=2"


def test_runtime_rejects_non_list_tool_calls_as_protocol_error():
    runtime = AgentRuntime(
        FakeClient([{"content": None, "tool_calls": {"name": "calculate"}, "finish_reason": "tool_calls"}]),
        create_default_registry(),
    )

    result = runtime.run([{"role": "user", "content": "bad response"}])

    assert result.status is RunStatus.FAILED
    assert result.error == "model protocol error: tool_calls must be a list"


def test_runtime_rejects_non_object_response():
    runtime = AgentRuntime(FakeClient([None]), create_default_registry())

    result = runtime.run([{"role": "user", "content": "bad response"}])

    assert result.status is RunStatus.FAILED
    assert result.error == "model protocol error: response must be an object"
