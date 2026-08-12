"""
Tool implementations for the mini-agent.

Each tool is a callable that takes keyword arguments and returns a string result.
Tools are registered in a registry that maps names to (function, description) pairs.
"""

import math
import random
from datetime import datetime, timezone as dt_timezone, timedelta
from typing import Any, Callable

# ─── Tool Registry ────────────────────────────────────────────────────────────

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


# ─── Tool Implementations ─────────────────────────────────────────────────────

def get_weather(city: str, unit: str = "celsius") -> str:
    """Get weather for a city (simulated with realistic data)."""
    # Simulated weather data for various cities
    weather_data = {
        "北京": {"temp": 28, "condition": "晴", "humidity": 45, "wind": "北风 3级"},
        "上海": {"temp": 31, "condition": "多云", "humidity": 72, "wind": "东南风 2级"},
        "广州": {"temp": 33, "condition": "雷阵雨", "humidity": 85, "wind": "南风 2级"},
        "深圳": {"temp": 32, "condition": "阵雨", "humidity": 80, "wind": "西南风 3级"},
        "杭州": {"temp": 30, "condition": "阴", "humidity": 65, "wind": "东风 2级"},
        "成都": {"temp": 26, "condition": "小雨", "humidity": 78, "wind": "微风"},
        "重庆": {"temp": 35, "condition": "晴", "humidity": 55, "wind": "北风 1级"},
        "武汉": {"temp": 34, "condition": "晴", "humidity": 60, "wind": "南风 3级"},
        "南京": {"temp": 29, "condition": "多云", "humidity": 68, "wind": "东风 2级"},
        "西安": {"temp": 27, "condition": "晴", "humidity": 40, "wind": "西北风 2级"},
        "Tokyo": {"temp": 29, "condition": "Partly Cloudy", "humidity": 70, "wind": "SE 5km/h"},
        "London": {"temp": 18, "condition": "Overcast", "humidity": 82, "wind": "W 12km/h"},
        "Paris": {"temp": 22, "condition": "Sunny", "humidity": 55, "wind": "NW 8km/h"},
        "New York": {"temp": 26, "condition": "Clear", "humidity": 60, "wind": "S 10km/h"},
        "San Francisco": {"temp": 19, "condition": "Foggy", "humidity": 88, "wind": "W 15km/h"},
        "Berlin": {"temp": 20, "condition": "Rain", "humidity": 75, "wind": "SW 14km/h"},
        "Sydney": {"temp": 15, "condition": "Cool", "humidity": 65, "wind": "S 20km/h"},
    }

    data = weather_data.get(city)
    if data is None:
        # Generate random weather for unknown cities
        conditions = ["晴", "多云", "阴", "小雨", "大风"]
        data = {
            "temp": random.randint(10, 38),
            "condition": random.choice(conditions),
            "humidity": random.randint(30, 90),
            "wind": "微风",
        }

    temp = data["temp"]
    if unit == "fahrenheit":
        temp = round(temp * 9 / 5 + 32, 1)
        unit_symbol = "°F"
    else:
        unit_symbol = "°C"

    return (
        f"🌍 {city} 天气\n"
        f"   天气: {data['condition']}\n"
        f"   温度: {temp}{unit_symbol}\n"
        f"   湿度: {data['humidity']}%\n"
        f"   风力: {data['wind']}"
    )


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    # Allowed names for safe eval
    allowed = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "log10": math.log10,
        "log2": math.log2, "exp": math.exp, "pow": pow,
        "pi": math.pi, "e": math.e,
        "ceil": math.ceil, "floor": math.floor,
    }

    try:
        # Validate: only allow safe characters
        safe_expr = expression.replace("**", "^")  # display hint
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"🧮 计算结果\n   表达式: {expression}\n   结果: {result}"
    except Exception as e:
        return f"❌ 计算错误\n   表达式: {expression}\n   错误: {e}"


def get_current_time(timezone: str = "UTC") -> str:
    """Get current time in a specified timezone."""
    # Common timezone offsets (simplified)
    tz_offsets = {
        "UTC": 0,
        "Asia/Shanghai": 8,
        "Asia/Tokyo": 9,
        "Asia/Seoul": 9,
        "Asia/Kolkata": 5.5,
        "Asia/Dubai": 4,
        "Europe/London": 1,
        "Europe/Paris": 2,
        "Europe/Berlin": 2,
        "Europe/Moscow": 3,
        "America/New_York": -4,
        "America/Chicago": -5,
        "America/Denver": -6,
        "America/Los_Angeles": -7,
        "America/Sao_Paulo": -3,
        "Pacific/Auckland": 12,
        "Australia/Sydney": 10,
    }

    offset_hours = tz_offsets.get(timezone)
    if offset_hours is None:
        return f"❌ 未知时区: {timezone}\n   支持的时区: {', '.join(sorted(tz_offsets.keys()))}"

    tz = dt_timezone(timedelta(hours=offset_hours))
    now = datetime.now(tz)

    return (
        f"🕐 当前时间\n"
        f"   时区: {timezone} (UTC{'+' if offset_hours >= 0 else ''}{offset_hours})\n"
        f"   时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"   星期: {['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}"
    )


def translate(text: str, target_language: str, source_language: str = "auto") -> str:
    """Translate text (simulated with common phrases)."""
    # Simulated translation dictionary
    translations = {
        ("你好", "English"): "Hello",
        ("Hello", "Chinese"): "你好",
        ("Hello World", "Chinese"): "你好，世界",
        ("你好，世界", "English"): "Hello World",
        ("谢谢", "English"): "Thank you",
        ("Thank you", "Chinese"): "谢谢",
        ("再见", "English"): "Goodbye",
        ("Goodbye", "Chinese"): "再见",
        ("早上好", "English"): "Good morning",
        ("Good morning", "Chinese"): "早上好",
        ("我爱你", "English"): "I love you",
        ("I love you", "Chinese"): "我爱你",
    }

    # Try exact match
    result = translations.get((text, target_language))
    if result:
        return f"🌐 翻译结果\n   原文: {text}\n   目标语言: {target_language}\n   译文: {result}"

    # Simulate translation by adding a prefix/suffix
    lang_map = {
        "English": "[EN]", "Chinese": "[中]", "Japanese": "[日]",
        "Korean": "[한]", "French": "[FR]", "German": "[DE]",
        "Spanish": "[ES]", "Russian": "[RU]",
    }
    prefix = lang_map.get(target_language, f"[{target_language}]")

    return (
        f"🌐 翻译结果\n"
        f"   原文: {text}\n"
        f"   源语言: {source_language}\n"
        f"   目标语言: {target_language}\n"
        f"   译文: {prefix} {text}"
    )


def search_knowledge(query: str, max_results: int = 3) -> str:
    """Search a simulated knowledge base."""
    # Simulated knowledge entries
    knowledge = [
        {"topic": "Rust", "content": "Rust 是一门注重安全和性能的系统编程语言，由 Mozilla 开发，2015 年发布 1.0。"},
        {"topic": "Python", "content": "Python 是一门通用高级编程语言，以简洁易读著称，广泛用于 AI、Web、数据科学等领域。"},
        {"topic": "Agent", "content": "AI Agent 是能够自主感知环境、做出决策并执行动作的智能体，核心循环为：感知→思考→行动。"},
        {"topic": "LLM", "content": "大语言模型 (LLM) 是基于 Transformer 架构的神经网络，通过海量文本训练，具备理解和生成自然语言的能力。"},
        {"topic": "Tool Calling", "content": "Tool Calling 是 LLM 与外部工具交互的机制：模型生成工具调用请求，由运行时执行后将结果返回模型。"},
        {"topic": "SSE", "content": "Server-Sent Events (SSE) 是一种 HTTP 长连接协议，允许服务器向客户端推送实时更新流。"},
        {"topic": "mini-agent-runtime", "content": "mini-agent-runtime 是一个轻量级 AI Agent 运行时，包含 Rust 服务端和 Python Agent 端，演示完整的 Agent 工作流。"},
    ]

    # Simple keyword matching
    results = []
    query_lower = query.lower()
    for entry in knowledge:
        if entry["topic"].lower() in query_lower or any(
            word in query_lower for word in entry["content"].lower().split()
        ):
            results.append(entry)
        if len(results) >= max_results:
            break

    if not results:
        return f"🔍 未找到与 \"{query}\" 相关的知识条目。"

    formatted = f"🔍 搜索 \"{query}\" 找到 {len(results)} 条结果:\n"
    for i, r in enumerate(results, 1):
        formatted += f"\n   [{i}] {r['topic']}\n       {r['content']}"

    return formatted


# ─── Default Registry Factory ─────────────────────────────────────────────────

def create_default_registry() -> ToolRegistry:
    """Create a tool registry with all default tools registered."""
    registry = ToolRegistry()

    registry.register(
        name="get_weather",
        description="Get the current weather for a given city. Returns temperature, condition, humidity, and wind.",
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name, e.g. 'Beijing' or 'New York'",
                },
                "unit": {
                    "type": "string",
                    "description": "Temperature unit: 'celsius' or 'fahrenheit'",
                    "enum": ["celsius", "fahrenheit"],
                },
            },
            "required": ["city"],
        },
        func=get_weather,
    )

    registry.register(
        name="calculate",
        description="Evaluate a mathematical expression. Supports +, -, *, /, **, sqrt, sin, cos, tan, log, pi, e.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate, e.g. '2 ** 10' or 'sqrt(144)'",
                },
            },
            "required": ["expression"],
        },
        func=calculate,
    )

    registry.register(
        name="get_current_time",
        description="Get the current date and time in a specified timezone.",
        parameters={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name, e.g. 'Asia/Shanghai', 'America/New_York', 'UTC'",
                },
            },
            "required": ["timezone"],
        },
        func=get_current_time,
    )

    registry.register(
        name="translate",
        description="Translate text from one language to another.",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to translate",
                },
                "target_language": {
                    "type": "string",
                    "description": "Target language name, e.g. 'English', 'Chinese', 'Japanese'",
                },
                "source_language": {
                    "type": "string",
                    "description": "Source language name (default: auto-detect)",
                },
            },
            "required": ["text", "target_language"],
        },
        func=translate,
    )

    registry.register(
        name="search_knowledge",
        description="Search a local knowledge base for relevant information.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 3)",
                },
            },
            "required": ["query"],
        },
        func=search_knowledge,
    )

    return registry
