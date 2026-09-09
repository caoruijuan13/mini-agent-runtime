# mini-agent-runtime

`mini-agent-runtime` 是一个面向学习和实验的 AI Agent 运行时。项目把系统拆成两个明确层次：Rust 服务负责 HTTP 接口、模型访问和工具描述；Python Agent 负责对话状态、工具执行与终端交互。

## 项目目标

- 用较少代码展示完整的模型调用和工具调用链路。
- 在没有 API Key 时，通过 Mock 模式完成开发、测试和压测。
- 为并发、流式传输、模型网关、可观测性和可靠性实验提供基础。
- 保持 OpenAI Chat Completions 兼容的模型接入边界。

## 当前能力

| 模块 | 能力 |
| --- | --- |
| Rust 服务 | Axum HTTP、Tokio 异步运行时、JSON/SSE、CORS、Tracing |
| 模型客户端 | OpenAI 兼容请求、工具 Schema、Mock 响应 |
| Python Agent | 多轮历史、最多 10 次工具循环、回调、终端命令 |
| 工具 | 天气、计算、时间、翻译、本地知识搜索 |
| 工程质量 | Rust/Python 测试、隔离 Mock 集成测试、JSON QA 报告 |
| 性能基线 | 固定负载、并发测试、延迟、TTFT、吞吐量、CPU/RSS |

!!! note "证据边界"
    默认基准使用 Mock 模型，只衡量当前机器上的网关、序列化和 HTTP/SSE 传输开销。它不代表真实大模型延迟、GPU 推理吞吐量或生产容量。

## 阅读顺序

1. 按[快速开始](getting-started.md)运行 Mock 演示。
2. 阅读[架构设计](architecture.md)和[Agent 循环](agent-loop.md)。
3. 通过[服务接口](server-api.md)直接调用 Rust 服务。
4. 使用[QA 与测试](quality.md)建立确定性状态。
5. 使用[性能基线](performance.md)比较优化前后的结果。
6. 按[开发与扩展](development.md)增加 Provider、工具或基础设施能力。

长期学习与项目演进请按[学习与优化路线图](roadmap.md)推进，逐阶段完成故障实验和验收。

## 代码入口

- `src/main.rs`：Rust 服务启动入口。
- `src/server.rs`：路由、请求和响应类型。
- `src/llm.rs`：真实模型与 Mock 模型客户端。
- `src/tools.rs`：提交给模型的工具定义。
- `python/agent/agent.py`：薄会话适配层。
- `python/agent/runtime.py`：规范运行时核心。
- `python/agent/tools.py`：工具实际实现。
- `python/agent/client.py`：JSON/SSE HTTP 客户端。
