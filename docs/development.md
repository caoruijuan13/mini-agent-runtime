# 开发与扩展

## 推荐工作流

```text
阅读契约
  → 修改代码和测试
  → bash scripts/test.sh
  → bash scripts/docs.sh build
  → bash scripts/benchmark.sh（性能相关修改）
  → 检查报告和差异
```

## 修改 Rust 服务

主要文件：

- `src/main.rs`：初始化、监听和启动日志。
- `src/server.rs`：HTTP 类型、路由和处理器。
- `src/config.rs`：环境配置和启动校验。
- `src/llm.rs`：Provider 请求、响应和 SSE 解析。
- `src/tools.rs`：模型可见的工具 Schema。

新增共享状态时，应先明确并发模型、锁粒度和生命周期。不要在 Axum 异步处理器中直接执行长时间阻塞操作。

## 修改 Python Agent

主要文件：

- `python/agent/agent.py`：薄会话适配层。
- `python/agent/runtime.py`：状态转换、预算和事件。
- `python/agent/client.py`：服务客户端和 SSE 解码。
- `python/agent/tools.py`：工具注册与执行。
- `python/agent/__main__.py`：CLI 和展示回调。

修改消息格式时，应同时检查 Rust 的 `ChatMessage`、真实 Provider 兼容性、Runtime 历史结构和 `RunResult` 契约。

## 增加 Provider

当前所有真实后端共用 `openai` 分支。要支持不兼容协议，建议：

1. 抽象统一 Provider trait。
2. 定义内部请求、响应和错误类型。
3. 每个适配器负责外部协议转换。
4. 保留 Mock Provider 作为确定性测试替身。
5. 为 429、5xx、超时和畸形响应增加契约测试。

## 增加 API

新增路由时至少补充：

- 请求与响应结构。
- 正常和错误状态码测试。
- 输入大小与字段约束。
- 是否需要认证和限流。
- 是否写入共享状态。
- 文档和 curl 示例。

## 性能修改

先保存修改前报告，再保持完全相同的负载契约运行修改后报告。至少比较：

- 吞吐量。
- p95/p99 延迟。
- TTFT。
- 错误率。
- CPU/RSS。
- 重复性 CV。

一次只改变一个主要因素；否则无法把收益归因到具体实现。

## 文档维护

- 代码行为改变时同步修改对应章节。
- 新页面必须加入 `mkdocs.yml` 的 `nav`。
- 使用相对链接连接文档页面。
- 不在文档中固化密钥或本地 `.env` 内容。
- 历史性能数字必须标注日期、环境和 Mock/真实模型边界。
- 提交前运行严格构建。
