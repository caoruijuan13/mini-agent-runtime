# mini-agent-runtime

由学习者主导、随学习逐步生长的 Python Agent Runtime 项目。
当前先学习消息、模型响应和工具调用；不预先引入网关、部署或并发基础设施。

## 从哪里开始

先读[学习指南](docs/learning.md)，确定这一阶段要回答的问题和验收标准，
再决定需要生成或修改哪些代码。已有 Python 代码是参考基线，不代表你已完成学习。

| 文件 | 当前参考内容 |
| --- | --- |
| `python/agent/mock.py` | 固定规则的模型响应 |
| `python/agent/tools.py` | 最小加法工具与注册器 |
| `python/agent/runtime.py` | 模型与工具执行循环 |
| `python/agent/agent.py` | 会话历史 |
| `python/agent/__main__.py` | 简单命令行 |

如需观察已有基线，在项目根目录运行：

```bash
bash scripts/run_demo.sh 'add 2 3' --trace
```

只需 Python 3.10+ 标准库，无网络、API Key 或其它语言工具链。
这个命令演示了多个概念；第一阶段只需研究模型输入输出，不必一次读完整个循环。

## 协作方式

- 由你确定阶段、问题、实现范围和推进时机。
- 默认先解释、讨论设计和验收；你提出实现请求后才生成对应代码。
- 一次实现当前明确要求的部分，不提前完成后续阶段。
- 测试通过只表示代码行为经过检查；学习完成由你确认。

后续主题只作为[候选路线](docs/roadmap.md)，不自动推进。

## 验证与文档

```bash
python3 -m pip install -r python/requirements.txt
bash scripts/test.sh
python3 -m pip install -r requirements-docs.txt
bash scripts/docs.sh build
```

文档预览：`bash scripts/docs.sh serve`。

本轮移除了 Rust 网关、Cargo 文件、HTTP 客户端、模拟业务工具、网关集成测试、
压测脚本和对应文档。保留的 Python 核心可独立运行。
