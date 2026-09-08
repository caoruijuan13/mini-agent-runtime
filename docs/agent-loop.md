# Agent 循环

核心实现位于 `python/agent/agent.py`。

## 消息状态

首次调用时，Agent 自动加入 system prompt；之后每轮在同一个 `messages` 列表中追加消息。

```json
[
  {"role": "system", "content": "..."},
  {"role": "user", "content": "计算 2 + 2"},
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "calculate", "arguments": "{\"expression\":\"2 + 2\"}"}}]
  },
  {"role": "tool", "tool_call_id": "call_1", "name": "calculate", "content": "..."}
]
```

`reset()` 会清空全部历史，下一次对话重新注入 system prompt。

## 状态机

```text
append user message
        │
        ▼
call Rust /chat
        │
        ├─ no tool_calls / finish_reason=stop ─→ append final text ─→ return
        │
        └─ tool_calls
             ├─ append assistant tool request
             ├─ parse arguments
             ├─ execute each local tool
             ├─ append each tool result
             └─ repeat
```

循环最多执行 `MAX_ITERATIONS = 10` 次，防止模型持续请求工具形成无限循环。

## 错误行为

- 工具名不存在：注册表返回错误文本，随后作为工具结果交回模型。
- 工具函数抛出异常：异常被转换为错误文本。
- 工具参数不是有效 JSON：当前实现退化为空对象，可能导致缺少必填参数。
- HTTP 或模型错误：`requests` 异常向 CLI 冒泡，由终端主循环显示后继续接受输入。
- 达到最大迭代次数：返回中文警告文本。

!!! warning "错误语义"
    工具失败当前仍被编码为普通字符串，没有结构化 `is_error` 字段。模型只能根据文本推断失败。生产化时应改成明确的错误类型、错误码与可重试属性。

## 回调

Agent 支持三个可选回调：

- `on_tool_call(name, args)`
- `on_tool_result(name, result)`
- `on_stream_chunk(chunk)`

CLI 用它们渲染终端输出。回调属于展示接口，不应改变 Agent 状态或执行第二次工具调用。

## 扩展建议

- 把一轮执行建模为显式状态机。
- 为请求、模型调用和工具调用引入超时预算。
- 对工具参数执行 JSON Schema 校验。
- 区分可重试错误、永久错误和用户取消。
- 为消息数量和上下文 Token 设置上限。
