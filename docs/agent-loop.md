# Agent 循环

核心实现位于 `python/agent/runtime.py`；`python/agent/agent.py` 只是会话适配层。

## 消息状态

是否加入 system prompt 由应用适配层显式决定；Runtime 不内置人格、语言或产品策略。

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

循环最多执行 `RuntimeConfig.max_steps = 10` 次，防止模型持续请求工具形成无限循环。

达到上限时返回 `RunStatus.MAX_STEPS`，而不是在运行内核中拼接面向用户的提示文本。

## 终态与事件

一次 `AgentRuntime.run()` 返回 `RunResult`：

- `COMPLETED`：收到没有工具调用的最终模型响应。
- `MAX_STEPS`：达到运行预算。
- `FAILED`：模型客户端抛出异常。

Runtime 通过 `RuntimeEvent` 发出 `model_requested`、`model_responded`、`tool_requested`、`tool_completed`、`run_completed`、`run_failed` 和 `run_max_steps`。

## 错误行为

- 工具名不存在：注册表返回错误文本，随后作为工具结果交回模型。
- 工具函数抛出异常：异常被转换为错误文本。
- 工具参数不是有效 JSON：Runtime 生成工具错误结果，不再静默退化为空对象。
- HTTP 或模型错误：Runtime 记录 `FAILED` 终态和错误文本；应用适配层决定如何展示或重试。
- 达到最大迭代次数：返回中文警告文本。

!!! warning "错误语义"
    工具失败当前仍被编码为普通字符串，没有结构化 `is_error` 字段。模型只能根据文本推断失败。生产化时应改成明确的错误类型、错误码与可重试属性。

## 观察者

应用可以订阅统一的 `on_event(RuntimeEvent)`。CLI 只观察工具请求和工具结果并负责渲染；展示逻辑不应改变 Runtime 状态，也不应执行第二次工具调用。

## 扩展建议

- 为 Runtime 增加总时间预算和取消令牌。
- 为请求、模型调用和工具调用引入超时预算。
- 对工具参数执行 JSON Schema 校验。
- 区分可重试错误、永久错误和用户取消。
- 为消息数量和上下文 Token 设置上限。
