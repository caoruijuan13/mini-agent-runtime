"""工具注册与执行：模型只提出调用，真正的函数由程序执行。"""

from typing import Callable

class ToolRegistry:
    """Registry that holds tool functions and their metadata."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, parameters: dict, func: Callable):
        """Register a new tool."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
        }

    def get(self, name: str) -> dict | None:
        return self._tools.get(name)

    def execute(self, name: str, arguments: dict) -> str:
        """Execute a tool by name with given arguments. Returns result string."""
        tool = self.get(name)
        if tool is None:
            return f"Error: Unknown tool '{name}'"
        try:
            result = tool["func"](**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {e}"

    def list_tools(self) -> list[dict]:
        """Return tool metadata (without functions) for API calls."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
            for t in self._tools.values()
        ]

    @property
    def names(self) -> list[str]:
        return list(self._tools.keys())


def add(a: float, b: float) -> float:
    """最小工具：没有网络、文件或表达式解释器。"""
    return a + b


def create_learning_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        "add", "Add two numbers",
        {"type": "object", "properties": {
            "a": {"type": "number"}, "b": {"type": "number"},
        }, "required": ["a", "b"]},
        add,
    )
    return registry
