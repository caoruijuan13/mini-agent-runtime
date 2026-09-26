# 验证当前代码

```bash
python3 -m pip install -r python/requirements.txt
bash scripts/test.sh
```

执行 `tests/` 中全部 Python 测试，不启动服务，不访问网络。

- `test_learning.py`：本地调用闭环、多轮历史、注入客户端、步数终止和标准库启动。
- `test_runtime.py`：模型响应结构、工具参数和最大步数。

原网关、SSE、模拟业务工具及基准测试随对应代码移除，不再列作当前验收能力。
测试通过证明现有参考代码满足测试场景，不表示学习者已掌握全部内容。

## 文档检查

```bash
python3 -m pip install -r requirements-docs.txt
bash scripts/docs.sh build
```

严格构建检查导航和链接。后续仅为明确请求的实现添加适当验证。
