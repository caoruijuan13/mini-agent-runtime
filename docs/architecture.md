# 架构设计

## 组件关系

```text
User
  │ terminal input
  ▼
Python CLI ── Agent ── Local Tool Registry
                 │
                 │ OpenAI-style messages over HTTP
                 ▼
          Rust/Axum Server
          ├─ /health
          ├─ /tools
          └─ /chat
                 │
                 ▼
      Mock or OpenAI-compatible LLM
```

## 职责边界

### Python Agent

Python 层拥有会话和行动能力：

- 保存 system、user、assistant、tool 消息。
- 判断模型响应是最终文本还是工具请求。
- 解析工具参数并执行本地函数。
- 把工具结果追加到消息历史后再次调用模型。
- 通过回调向终端显示工具调用、结果和文本。

### Rust 服务

Rust 层是无状态模型网关：

- 校验并反序列化 HTTP 请求。
- 将工具定义转换为 OpenAI 兼容 JSON Schema。
- 调用真实模型端点或生成 Mock 响应。
- 将结果转换为统一 JSON 或 SSE 响应。
- 提供健康状态和工具清单。

当前对话历史由调用方提交，Rust 服务不保存会话。

### 工具定义与实现

工具存在两份信息：

| 位置 | 内容 | 消费者 |
| --- | --- | --- |
| `src/tools.rs` | 名称、描述、参数 Schema | 模型 |
| `python/agent/tools.py` | 相同元数据和 Python 函数 | Agent |

因此新增或修改工具时必须同步两端。Rust 服务只告诉模型“可以调用什么”，真正执行发生在 Python 进程。

## 关键数据流

普通对话：

```text
user → Python history → POST /chat → LLM → text → terminal
```

工具调用：

```text
user
  → /chat
  → assistant(tool_calls)
  → Python tool execution
  → tool result appended to history
  → /chat
  → final assistant text
```

流式服务接口：

```text
LLM byte stream → Rust SSE parser → Axum SSE events → HTTP client
```

Python CLI 当前并未把最终回答接入这条完整流式链路，详见[模型与流式传输](llm-streaming.md)。

## 运行时状态

Rust 的 `AppState` 由 `Arc` 共享，包括：

- `Config`
- `LlmClient`
- `ToolRegistry`

当前状态均为只读或内部可共享客户端，因此请求处理器可以并发访问。项目尚未实现租户状态、队列、限流器或持久化。

## 设计取舍

- Rust 负责网络和模型访问，便于学习异步服务性能。
- Python 负责工具生态和 Agent 行为，便于快速扩展。
- Mock 模式提供无需密钥的确定性工程验证。
- HTTP 边界让两种语言保持解耦，但增加序列化和部署复杂度。
