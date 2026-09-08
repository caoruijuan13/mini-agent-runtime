# 配置说明

Rust 服务启动时先尝试读取项目根目录 `.env`，已存在的进程环境变量优先于文件值。

## 环境变量

| 变量 | 默认值 | 约束或说明 |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | 监听地址；解析失败时进程退出 |
| `PORT` | `3000` | 无法解析时回退到默认值 |
| `LLM_PROVIDER` | `mock` | 实际支持路径为 `mock` 或 `openai` |
| `OPENAI_API_KEY` | 空 | `LLM_PROVIDER=openai` 时必须非空 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 请求会追加 `/chat/completions` |
| `MODEL` | `gpt-4o-mini` | 原样提交给兼容端点 |
| `MAX_TOKENS` | `2048` | 启动校验范围为 1～128000 |
| `TEMPERATURE` | `0.7` | 当前未限制范围，交由 Provider 校验 |
| `RUST_LOG` | 项目级 info | Tracing 过滤表达式 |

## Mock 配置

```dotenv
HOST=127.0.0.1
PORT=3000
LLM_PROVIDER=mock
MODEL=mock-baseline
RUST_LOG=mini_agent_server=info
```

Mock 通过关键词选择工具调用，不使用 `OPENAI_API_KEY`。

## OpenAI 兼容配置

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=replace-me
OPENAI_BASE_URL=https://provider.example/v1
MODEL=provider-model-name
MAX_TOKENS=2048
TEMPERATURE=0.7
```

兼容性至少包括：

- `POST /chat/completions`。
- OpenAI 风格 `messages`。
- 非流式 `choices[0].message`。
- 如果使用工具，需要兼容 `tools`、`tool_choice` 和 `tool_calls`。
- 如果使用服务端流式接口，需要兼容 SSE `choices[0].delta.content`。

## 配置与测试隔离

生产入口使用 `Config::from_env()`；Rust 测试使用纯 `Config::default()`。QA 还显式设置 `LLM_PROVIDER=mock`，因此开发者本地 `.env` 不会让自动测试意外调用付费模型。

## 安全建议

- 使用密钥管理服务或运行环境注入密钥。
- 日志中不要输出 Authorization 头或完整请求配置。
- 对外监听前增加认证、TLS、限流和 CORS 白名单。
- 不要直接信任用户传入的模型名称、Base URL 或 Token 上限。
