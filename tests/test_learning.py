"""学习入口的行为验收：真实执行核心循环，不启动服务器。"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from agent.agent import Agent
from agent.runtime import RunStatus


def test_local_tool_round_trip_and_history():
    agent = Agent()
    first = agent.run("add 2 3")
    assert first.status is RunStatus.COMPLETED
    assert first.content == "5.0"
    assert first.steps == 2
    assert [m["role"] for m in first.messages] == ["user", "assistant", "tool", "assistant"]
    assert first.messages[1]["tool_calls"][0]["id"] == first.messages[2]["tool_call_id"]
    second = agent.run("add 4 5")
    assert second.content == "9.0"
    assert second.messages[:4] == first.messages
    assert second.messages[5]["tool_calls"][0]["id"] != first.messages[1]["tool_calls"][0]["id"]
    agent.reset()
    assert agent.messages == []
    assert agent.run("你好").steps == 1


def test_step_budget_does_not_misreport_tool_result_as_final_answer():
    result = Agent(max_steps=1).run("add 2 3")
    assert result.status is RunStatus.MAX_STEPS
    assert result.content is None
    assert result.messages[-1]["role"] == "tool"
    assert result.messages[-1]["content"] == "5.0"


def test_invalid_learning_command_never_dispatches_tool():
    events = []
    agent = Agent(on_event=events.append)
    assert agent.run("add two 3").content == "用法：add 2 3"
    assert "tool_requested" not in [event.kind for event in events]


def test_injected_client_receives_messages():
    class Client:
        def chat(self, messages, stream=False):
            assert messages == [{"role": "user", "content": "hello"}]
            return {"content": "custom response"}

    assert Agent(client=Client()).run("hello").content == "custom response"


@pytest.mark.parametrize("extra, code, expected", [
    ([], 0, "run_completed"),
    (["--max-steps", "1"], 1, "run_max_steps"),
])
def test_cli_runs_without_site_packages(extra, code, expected):
    # -S 禁止加载 site-packages，保证入门不依赖 requests/pytest 等外部库。
    result = subprocess.run(
        [sys.executable, "-S", "-m", "agent", "add 2 3", "--trace", *extra],
        cwd=ROOT / "python", capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == code, result.stderr
    assert expected in result.stdout
    assert "tool_completed" in result.stdout
