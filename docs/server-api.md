# 服务接口

默认地址为 `http://127.0.0.1:3000`。当前接口没有认证，且 CORS 允许任意来源，只适合本地开发或受控网络。

## `GET /health`

返回服务版本、Provider 和工具数量。

```json
{
  "status": "ok",
  "version": "0.1.0",
  "llm_provider": "mock",
  "tools_count": 5
}
```

健康接口只表明 Rust 服务能够响应，并不主动探测真实模型端点。

## `GET /tools`

返回模型可见的工具名称和描述，不返回完整参数 Schema。

```json
[
  {
    "name": "get_weather",
    "description": "Get the current weather for a given city. Returns temperature, condition, and humidity."
  }
]
```

## `POST /chat`

### 请求

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "你好"}
  ],
  "stream": false
}
```

字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `messages` | array | 是 | OpenAI 风格消息列表 |
| `stream` | boolean | 否 | 默认为 `false` |

消息支持 `role`、可空的 `content`、`tool_calls`、`tool_call_id` 和 `name`。服务当前没有对 role 枚举或消息数量做额外业务校验。

### 文本响应

```json
{
  "content": "你好！",
  "tool_calls": null,
  "finish_reason": "stop",
  "usage": {
    "prompt_tokens": 30,
    "completion_tokens": 50,
    "total_tokens": 80
  }
}
```

### 工具调用响应

```json
{
  "content": null,
  "tool_calls": [
    {
      "id": "call_example",
      "type": "function",
      "function": {
        "name": "calculate",
        "arguments": "{\"expression\":\"2 + 2\"}"
      }
    }
  ],
  "finish_reason": "tool_calls",
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 18,
    "total_tokens": 63
  }
}
```

`function.arguments` 是 JSON 字符串，不是已经解析的对象。

### SSE 响应

请求设置 `stream=true`，并建议发送 `Accept: text/event-stream`。每个事件的数据为：

```json
{"content": "增量文本或 null", "finish_reason": "stop 或 null"}
```

当前服务不会发出显式 `[DONE]` 事件；客户端应以流结束或非空 `finish_reason` 判断完成。

## 错误响应

模型调用失败时：

```json
{
  "error": "错误说明"
}
```

当前统一使用 HTTP 500，尚未区分上游 429、认证失败、请求错误和超时。生产网关应建立稳定错误码，并避免直接向外暴露可能包含敏感信息的上游响应。
