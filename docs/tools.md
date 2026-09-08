# 工具系统

## 内置工具

| 工具名 | 必填参数 | 当前实现 |
| --- | --- | --- |
| `get_weather` | `city` | 固定城市表；未知城市生成随机模拟值 |
| `calculate` | `expression` | 受限 Python `eval` 和部分 `math` 函数 |
| `get_current_time` | `timezone` | 固定时区偏移表 |
| `translate` | `text`, `target_language` | 常用短语映射，其余返回模拟前缀 |
| `search_knowledge` | `query` | 内存中的固定知识条目和简单关键词匹配 |

除当前时间和数学计算外，这些工具都是教学模拟，不应视为实时外部数据。

## 注册流程

Python 的 `ToolRegistry` 保存：

- 名称。
- 描述。
- 参数 Schema。
- 可调用函数。

执行时，Agent 根据模型返回的函数名查询注册表，然后以关键字参数调用函数。结果统一转换成字符串。

Rust 的 `ToolRegistry` 只保存定义，并通过 `to_openai_tools()` 转成模型请求中的 `tools` 数组。

## 新增工具

以 `get_status` 为例：

1. 在 `python/agent/tools.py` 实现函数。
2. 在 `create_default_registry()` 注册函数和参数 Schema。
3. 在 `src/tools.rs` 添加完全一致的模型侧定义。
4. 为正常输入、非法输入和未知工具增加 Python 测试。
5. 为 `/tools` 和完整 Agent 循环增加集成测试。
6. 运行 `bash scripts/test.sh`。

必须检查的同步项：

- 工具名称完全一致。
- 必填字段一致。
- 参数类型和枚举一致。
- Python 默认值与 Schema 中的可选性一致。
- 描述不应承诺实现无法提供的实时性或准确性。

## 安全边界

工具是执行边界，而不仅是普通函数。接入文件、命令、网络或外部账户时，应增加：

- 参数白名单和长度限制。
- 调用超时与取消。
- 最小权限。
- 输出大小限制。
- 敏感字段脱敏。
- 审计记录。
- 高风险动作确认。

`calculate` 虽然移除了 Python builtins，但仍不应作为面向不可信用户的通用表达式沙箱。生产实现应改用专用解析器和明确运算符白名单。
