"""确定性的教学模型替身，不是语言模型，也不进行推理。

输入 `add 2 3` 时提出工具调用；收到工具结果后返回最终文本。
其它输入直接回复。这样可以逐条观察协议，不需要 API Key 或服务。
"""

import json


class MockClient:
    def chat(self, messages: list[dict], stream: bool = False) -> dict:
        if stream:
            raise ValueError("教学 Mock 尚未实现流式输出")
        last = messages[-1]
        if last["role"] == "tool":
            return {"content": last["content"], "finish_reason": "stop"}
        text = last.get("content") or ""
        parts = text.split()
        if parts and parts[0] == "add":
            try:
                _, a, b = parts
                arguments = {"a": float(a), "b": float(b)}
            except ValueError:
                return {"content": "用法：add 2 3", "finish_reason": "stop"}
            return {
                "content": None,
                "tool_calls": [{
                    "id": f"call_{len(messages)}", "type": "function",
                    "function": {"name": "add", "arguments": json.dumps(arguments)},
                }],
                "finish_reason": "tool_calls",
            }
        return {"content": f"Mock 收到：{text}", "finish_reason": "stop"}
