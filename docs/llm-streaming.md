# 模型与流式传输

## Provider 模式

`LlmClient` 根据 `LLM_PROVIDER` 选择执行路径：

- `mock`：在 Rust 进程中按关键词生成文本或工具请求。
- `openai`：向 `{OPENAI_BASE_URL}/chat/completions` 发起请求。

真实模型请求包含：

- `model`
- `messages`
- `max_tokens`
- `temperature`
- `stream`
- `tools` 和 `tool_choice=auto`

因此任意后端只有在兼容这些字段和响应结构时才能直接接入。

## 非流式响应

Rust 从第一个 `choice` 提取：

- `message.content`
- `message.tool_calls`
- `finish_reason`
- `usage`

Provider 返回非成功 HTTP 状态时，服务将上游状态和响应文本包装为内部错误，目前统一向客户端返回 HTTP 500。

## 服务端 SSE

当 `/chat` 请求包含 `"stream": true` 时，Rust 将上游 SSE 转换成下列事件：

```text
data: {"content":"你","finish_reason":null}

data: {"content":"好","finish_reason":"stop"}
```

Python 客户端强制以 UTF-8 解析 `text/event-stream`，并兼容 `data:` 后有无空格。这样可以避免 `requests` 默认字符集造成中文 JSON 损坏。

## 当前限制

### Agent Runtime 当前不消费流式模型结果

`AgentRuntime` 当前只使用非流式 `client.chat()` 完成状态转换。CLI 也只展示完整终态，不再提供“先完整请求、再逐字符播放”的伪流式 API。这样运行时语义保持单一路径，避免把展示效果误认为真实 TTFT。

### 流式工具调用未实现

Rust 的流式解析当前只读取 `delta.content`，`delta_tool_calls` 始终为空。真实模型在流式模式返回工具参数增量时，这些数据不会被组装。

### 用量不可见

当前 SSE 响应没有传递 Token usage。性能报告会把 SSE Token 指标标记为 `not_reported`，不会用字符数伪装成 Token 数。

## 后续实现顺序

1. 为 Runtime 增加独立的流式事件执行协议，不把 SSE 字符直接塞进最终文本。
2. 按 tool call ID 和参数片段组装 `delta.tool_calls`。
3. 传播 finish reason、usage 和结构化错误事件。
4. 让 Python Agent 直接消费流，并在发现工具调用后切换到执行阶段。
5. 传播客户端断开和取消信号。
6. 使用现有 TTFT 基准比较改造前后结果。

相关测量契约见[性能基线](performance.md)。
