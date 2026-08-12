# mini-agent-runtime

A minimal yet full-featured AI agent runtime — **Rust server** + **Python agent** — built to understand agent internals, tool calling, and infrastructure-level performance.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Terminal                             │
│                    (Python Chat Interface)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Python Agent                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Agent Loop   │  │ Tool Registry│  │ Server Client (HTTP)   │ │
│  │ (ReAct)     │──│ (5 tools)    │  │ (JSON + SSE)           │ │
│  └─────────────┘  └──────────────┘  └───────────┬────────────┘ │
└──────────────────────────────────────────────────┼──────────────┘
                                                   │ HTTP/SSE
                                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Rust Server (:3000)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ HTTP Router  │  │ LLM Client   │  │ Tool Definitions       │ │
│  │ (axum)      │──│ (OpenAI API) │  │ (JSON Schema)          │ │
│  │             │  │ + Mock Mode   │  │                        │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   LLM Provider   │
                  │ (OpenAI / Mock)  │
                  └─────────────────┘
```

## Features

### Rust Server
- **High-performance HTTP** — Built on Axum + Tokio async runtime
- **LLM Proxy** — Proxies to OpenAI-compatible APIs with full tool-calling support
- **Mock Mode** — Built-in mock LLM for testing without API keys
- **SSE Streaming** — Real-time token streaming via Server-Sent Events
- **Tool Definitions** — Server-side tool registry with JSON Schema
- **CORS + Tracing** — Production-ready middleware stack
- **Config** — Environment-based configuration with `.env` support

### Python Agent
- **ReAct Loop** — Standard Reason+Act agent loop with tool calling
- **5 Built-in Tools** — Weather, Calculator, Time, Translator, Knowledge Search
- **Colorful Terminal** — Rich terminal UI with ANSI colors
- **Streaming Output** — Real-time response rendering
- **Slash Commands** — `/help`, `/tools`, `/clear`, `/history`, `/quit`
- **Callback System** — Extensible tool call/result hooks

### Testing & DevOps
- **Unit Tests** — Rust + Python test suites
- **Integration Tests** — End-to-end agent loop verification
- **Docker** — Multi-stage Dockerfile + docker-compose
- **Shell Scripts** — One-command demo and test runners

## Quick Start

### Prerequisites
- Rust (1.70+) — [install](https://rustup.rs)
- Python (3.10+)
- (Optional) OpenAI API key for real LLM

### 1. Run the Demo (Mock Mode)

```bash
# One-command demo — builds server, starts agent
bash scripts/run_demo.sh
```

### 2. Manual Start

```bash
# Terminal 1: Start Rust server
cargo run

# Terminal 2: Start Python agent
cd python
pip install -r requirements.txt
python -m agent
```

### 3. With Real LLM

```bash
# Copy the env example and edit it
cp .env.example .env
# Edit .env with your API key, then:
cargo run
```

#### 支持的大模型

所有兼容 OpenAI API 格式的大模型均可接入。以下是推荐选项：

| 提供商 | 模型 | 获取 Key | 特点 |
|--------|------|----------|------|
| **OpenAI** | `gpt-4o-mini` | [platform.openai.com](https://platform.openai.com) | Tool calling 最稳定 |
| **通义千问** | `qwen-plus` | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com/) | 国内首选，中文能力强 |
| **DeepSeek** | `deepseek-chat` | [platform.deepseek.com](https://platform.deepseek.com/) | 性价比高，推理能力强 |
| **月之暗面** | `moonshot-v1-8k` | [platform.moonshot.cn](https://platform.moonshot.cn/) | 长上下文支持好 |
| **智谱 AI** | `glm-4-flash` | [open.bigmodel.cn](https://open.bigmodel.cn/) | 免费额度多 |
| **硅基流动** | `Qwen/Qwen2.5-7B-Instruct` | [siliconflow.cn](https://siliconflow.cn/) | 支持多种开源模型 |
| **Groq** | `llama-3.3-70b-versatile` | [console.groq.com](https://console.groq.com/) | 超快推理，免费额度 |
| **Ollama** | `qwen2.5:7b` | [ollama.com](https://ollama.com/) | 本地运行，无需联网 |

#### 快速配置示例

```bash
# 通义千问
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-dashscope-key
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export MODEL=qwen-plus

# DeepSeek
export OPENAI_API_KEY=sk-your-deepseek-key
export OPENAI_BASE_URL=https://api.deepseek.com/v1
export MODEL=deepseek-chat

# Ollama (本地)
export OPENAI_API_KEY=ollama
export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
export MODEL=qwen2.5:7b
```

> 更多配置见 `.env.example`，包含 9 种大模型的预设。

## API Endpoints

| Method | Path      | Description                     |
|--------|-----------|---------------------------------|
| GET    | `/health` | Server health check             |
| POST   | `/chat`   | Chat completion (JSON or SSE)   |
| GET    | `/tools`  | List available tool definitions |

### Chat Request

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather in Beijing?"}
  ],
  "stream": false
}
```

### Chat Response

```json
{
  "content": null,
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"Beijing\", \"unit\": \"celsius\"}"
      }
    }
  ],
  "finish_reason": "tool_calls"
}
```

## Available Tools

| Tool               | Description                                |
|--------------------|--------------------------------------------|
| `get_weather`      | Get current weather for a city             |
| `calculate`        | Evaluate math expressions                  |
| `get_current_time` | Get current time in any timezone           |
| `translate`        | Translate text between languages           |
| `search_knowledge` | Search a local knowledge base              |

## Configuration

| Environment Variable | Default                  | Description                |
|---------------------|--------------------------|----------------------------|
| `HOST`              | `127.0.0.1`              | Server bind address        |
| `PORT`              | `3000`                   | Server port                |
| `LLM_PROVIDER`      | `mock`                   | `mock` or `openai`         |
| `OPENAI_API_KEY`    | —                        | OpenAI API key             |
| `OPENAI_BASE_URL`   | `https://api.openai.com/v1` | Custom API endpoint     |
| `MODEL`             | `gpt-4o-mini`            | LLM model name             |
| `MAX_TOKENS`        | `2048`                   | Max response tokens        |
| `TEMPERATURE`       | `0.7`                    | LLM temperature            |

## Testing

```bash
# Run all tests
bash scripts/test.sh

# Rust tests only
cargo test

# Python tests only
python -m pytest tests/ -v
```

## Docker

```bash
# Build and run server
docker build -t mini-agent .
docker run -p 3000:3000 -e LLM_PROVIDER=mock mini-agent

# Or use docker-compose
docker-compose up --build
```

## Project Structure

```
mini-agent-runtime/
├── src/
│   ├── main.rs          # Server entry point
│   ├── config.rs        # Environment configuration
│   ├── llm.rs           # LLM client (OpenAI + Mock)
│   ├── tools.rs         # Tool definitions & registry
│   └── server.rs        # HTTP router & handlers
├── python/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── __main__.py  # Terminal chat UI
│   │   ├── agent.py     # Agent core loop
│   │   ├── client.py    # HTTP/SSE client
│   │   └── tools.py     # Tool implementations
│   └── requirements.txt
├── tests/
│   ├── test_tools.py        # Tool unit tests
│   └── test_integration.py  # Integration tests
├── scripts/
│   ├── run_demo.sh      # One-command demo
│   └── test.sh          # Run all tests
├── Dockerfile
├── docker-compose.yml
├── Cargo.toml
└── README.md
```

## How It Works

1. **User** types a message in the Python terminal
2. **Agent** sends conversation history to the Rust server
3. **Server** proxies the request to the LLM (or generates mock response)
4. **LLM** returns either a text response or tool call requests
5. If **tool calls**: Agent executes tools locally, appends results, loops back to step 2
6. If **text response**: Agent displays it to the user

This is the classic **ReAct** (Reason + Act) pattern used by modern AI agents.

## License

MIT
