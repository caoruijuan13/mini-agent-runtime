# 性能基线

## 运行

```bash
bash scripts/benchmark.sh
```

脚本构建 release 二进制，强制启动本地 Mock 服务，预热后执行固定负载，最后生成 `artifacts/benchmark-report.json`。

快速冒烟：

```bash
bash scripts/benchmark.sh \
  --concurrency 1,5 \
  --requests-per-case 5 \
  --repetitions 1 \
  --report artifacts/benchmark-smoke-report.json
```

## 默认负载契约

| 维度 | 默认值 |
| --- | --- |
| 请求模式 | JSON 非流式、SSE 流式 |
| 内容长度 | short、medium、long；SSE 使用 short |
| 并发 | 1、5、10、20、50 |
| 每场景最少请求 | 50；高并发时至少为并发数的两倍 |
| 重复次数 | 3 |
| 预热 | 5 次 short JSON 请求 |
| 单请求超时 | 30 秒 |
| Provider | `mock` |

## 指标定义

Latency
: 客户端从开始请求到完整读取响应的端到端时间。

TTFT
: 客户端从开始请求到收到第一个非空 SSE `content` 事件的时间。

Request throughput
: 成功请求数除以场景墙钟时间。

Completion token throughput
: Provider 报告的 completion tokens 除以场景墙钟时间。SSE 当前不报告 usage，因此该字段为空。

Error rate
: 失败请求数除以请求总数，同时按异常文本聚合错误类别。

Resource samples
: 使用本机 `ps` 对服务进程进行尽力而为的 CPU 和 RSS 采样；远程服务或未传 PID 时不可用。

## 分位数

每个场景保存 mean、p50、p95、p99 和 max。容量判断优先观察 p95/p99，而不是只看均值。

样本量很小时，尾部分位数不稳定；因此 smoke 结果只能验证工具链，不能作为优化结论。

## 重复性门禁

每个场景跨三轮计算吞吐量变异系数：

```text
CV = population standard deviation / mean throughput
```

默认要求：

- 所有请求成功。
- 每个场景吞吐量 CV 不超过 `0.20`。

超过门限时脚本退出失败，并在 `repeatability_contract.unstable_cases` 中列出场景。只有硬件、软件版本和 workload contract 相同的报告才适合直接比较。

## 已验证基线

2026-09-01 的一次本机 Mock 基线完成 3,600 次请求、零错误，最大吞吐量 CV 为 14.61%。这些数字仅是历史执行证据，机器负载和代码变化都会使结果漂移；当前结论应以重新执行产生的报告为准。

## 解读边界

Mock 基线可以发现：

- Rust HTTP 和 JSON 开销。
- Python 客户端并发行为。
- 请求长度对序列化和传输的影响。
- SSE 事件粒度和客户端解析成本。

Mock 基线不能证明：

- 真实 Provider 延迟或稳定性。
- Token 生成速度。
- GPU 利用率、KV Cache 或批处理效率。
- 公网条件下的最大容量。

接入真实模型时应建立新的报告类型或明确 Provider 标签，不要覆盖 Mock 基线的证据含义。
