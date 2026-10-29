# 运行时参考

这是已有实现的参考说明，不要求在第一阶段阅读或接受其设计。

## 数据流

```text
用户输入 → Agent（会话历史） → AgentRuntime.run()
                                  ↓
                             client.chat(history)
                                  ↓
                     普通文本 ← 响应 → 工具调用
                        ↓                ↓
                     返回结果      ToolRegistry.execute()
                                         ↓
                                  追加工具结果并再次请求
```

默认 `client` 是本地 `MockClient`，也可以显式注入实验用客户端。
`ModelClient` 协议只描述调用边界。

## 消息顺序：以 Mock 为例

`Agent.run()` 每次接收一条新的用户输入，将它追加到已有会话历史，再把历史交给 Runtime。
Mock 读取历史中的最后一条消息并返回响应；它本身不修改历史。
Runtime 负责把响应记录为 `assistant` 消息、执行工具并记录 `tool` 消息。
这里的 `role` 表示消息内容的来源；上述 `assistant` 与 `tool` 消息由 Runtime 写入历史。

- 普通文本（例如 `你好`）：`user → assistant`。Mock 返回文本且没有 `tool_calls`，Runtime 追加最终的 `assistant` 消息并结束。
- 工具调用（`add 2 3`）：`user → assistant(tool_calls) → tool → assistant`。Mock 先返回调用 `add` 的请求；Runtime 记录请求、执行注册的工具，并将结果作为 `role: "tool"` 的消息写入历史。该消息用 `tool_call_id` 对应请求的 `id`。Runtime 随后再次调用 Mock；Mock 读取最后一条工具消息，返回其 `content` 作为最终文本，Runtime 再追加一条 `assistant` 消息并结束。

一次循环最多调用一次模型，但可以执行该次响应中的工具调用。如果 `max_steps=1` 且输入为 `add 2 3`，工具仍会执行，历史停在 `user → assistant(tool_calls) → tool`；由于没有第二轮模型调用来产生最终回答，结果为 `RunStatus.MAX_STEPS`，`content` 为 `None`。`finish_reason: "stop"` 由 Mock 在最终文本响应中返回；Runtime 对无工具调用的响应返回 `RunStatus.COMPLETED`。

## 阅读核心

- `mock.py`：教学响应；只识别 `add 数字 数字`，其它文本直接回显。
- `tools.py`：注册器与 `add` 函数；元数据和可执行函数分别保存。
- `runtime.py`：模型调用、工具执行、消息记录、步数预算和事件。
- `agent.py`：保存多轮历史，可注入自定义客户端。

## 终态与错误

| 情况 | 行为 |
| --- | --- |
| 响应无工具调用 | 返回 `completed` |
| 模型调用异常或响应结构错误 | 返回 `failed` |
| 达到最大模型轮数 | 返回 `max_steps` |
| 未知工具、参数解析失败、工具函数异常 | 把错误作为工具结果回传，模型可以继续 |
| 事件观察者抛异常 | 忽略观察者错误，不改变运行状态 |

工具结果是字符串；这里的 `completed` 表示循环结束，不等于答案正确。
注册器保存 Schema，但当前没有完整 JSON Schema 验证器。
最大步数不是超时，也不能撤销已完成的工具操作。

## 尚待完善的协议

Runtime 当前只实现非流式执行。
`finish_reason` 与工具字段的冲突检查、调用 ID 完整验证等仍需后续完善。
详见[边界](limitations.md)及[路线图](roadmap.md)。
