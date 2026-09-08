# QA 与测试

## 一键 QA

```bash
bash scripts/test.sh
```

入口会执行：

1. Rust 单元测试。
2. Rust debug 服务构建。
3. Python 工具、基准统计和 SSE 客户端单元测试。
4. 启动绑定随机本地端口的独立 Mock 服务。
5. 执行 Python 端到端测试。
6. 写入 `artifacts/qa-report.json`。

任何命令失败或集成测试被跳过，QA 都会返回非零退出状态。

## 确定性契约

- 强制 `LLM_PROVIDER=mock`。
- 固定 `MODEL=mock-baseline`。
- 测试服务使用随机可用端口。
- 集成测试通过 `TEST_SERVER_URL` 指向隔离服务。
- 不允许集成测试 skip。
- 本地 `.env` 不改变 Rust 单元测试默认配置。

## 报告结构

报告的顶层字段包括：

| 字段 | 说明 |
| --- | --- |
| `schema_version` | 报告 Schema 版本 |
| `kind` | 固定为 `mini-agent-runtime-qa` |
| `status` | `passed` 或 `failed` |
| `git_revision` | 执行时 HEAD；工作区可能仍有未提交修改 |
| `environment_contract` | 强制 Mock 配置和 skip 策略 |
| `checks` | 每个检查的状态、耗时、计数和失败输出尾部 |

`artifacts/` 被 Git 忽略，报告是本机证据，不是随源码维护的固定结论。

## 单独执行

```bash
cargo test
python3 -m pytest tests/test_tools.py -q
python3 -m pytest tests/test_integration.py -q
```

直接执行集成测试时，如果没有服务会被跳过。因此发布或回归判断应使用 `scripts/test.sh`，而不是把单独 pytest 的零退出状态当作完整通过。

## 文档质量

```bash
python3 -m pip install -r requirements-docs.txt
bash scripts/docs.sh build
```

文档构建使用严格模式；导航遗漏、坏链接和无效锚点会阻止构建。
