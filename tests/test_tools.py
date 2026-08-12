"""
Unit tests for the tool implementations.
"""

import sys
import os
import math
import pytest

# Add parent directory to path so we can import agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from agent.tools import (
    get_weather,
    calculate,
    get_current_time,
    translate,
    search_knowledge,
    create_default_registry,
)


class TestGetWeather:
    """Tests for the get_weather tool."""

    def test_known_city_celsius(self):
        result = get_weather("北京", unit="celsius")
        assert "北京" in result
        assert "°C" in result
        assert "天气" in result

    def test_known_city_fahrenheit(self):
        result = get_weather("Tokyo", unit="fahrenheit")
        assert "Tokyo" in result
        assert "°F" in result

    def test_unknown_city_returns_random(self):
        result = get_weather("Atlantis")
        assert "Atlantis" in result
        assert "天气" in result

    def test_default_unit_is_celsius(self):
        result = get_weather("上海")
        assert "°C" in result

    def test_multiple_cities(self):
        cities = ["北京", "上海", "广州", "深圳", "London", "Paris", "New York"]
        for city in cities:
            result = get_weather(city)
            assert city in result


class TestCalculate:
    """Tests for the calculate tool."""

    def test_basic_arithmetic(self):
        result = calculate("2 + 3")
        assert "5" in result

    def test_multiplication(self):
        result = calculate("123 * 456")
        assert "56088" in result

    def test_division(self):
        result = calculate("10 / 3")
        assert "3.333" in result

    def test_power(self):
        result = calculate("2 ** 10")
        assert "1024" in result

    def test_sqrt(self):
        result = calculate("sqrt(144)")
        assert "12" in result

    def test_trig_functions(self):
        result = calculate("sin(0)")
        assert "0" in result

    def test_constants(self):
        result = calculate("pi")
        assert "3.14159" in result

    def test_complex_expression(self):
        result = calculate("sqrt(3**2 + 4**2)")
        assert "5" in result

    def test_invalid_expression(self):
        result = calculate("invalid_stuff")
        assert "错误" in result or "Error" in result

    def test_log(self):
        result = calculate("log(e)")
        assert "1" in result


class TestGetCurrentTime:
    """Tests for the get_current_time tool."""

    def test_utc(self):
        result = get_current_time("UTC")
        assert "UTC" in result
        assert "当前时间" in result

    def test_shanghai(self):
        result = get_current_time("Asia/Shanghai")
        assert "Asia/Shanghai" in result
        assert "+8" in result

    def test_new_york(self):
        result = get_current_time("America/New_York")
        assert "America/New_York" in result

    def test_unknown_timezone(self):
        result = get_current_time("Mars/Olympus")
        assert "未知时区" in result

    def test_weekday_included(self):
        result = get_current_time("UTC")
        assert "星期" in result


class TestTranslate:
    """Tests for the translate tool."""

    def test_hello_to_english(self):
        result = translate("你好", "English")
        assert "Hello" in result

    def test_hello_world_to_chinese(self):
        result = translate("Hello World", "Chinese")
        assert "你好" in result

    def test_unknown_phrase(self):
        result = translate("some random text", "Japanese")
        assert "翻译结果" in result
        assert "some random text" in result

    def test_multiple_languages(self):
        for lang in ["English", "Chinese", "Japanese", "French"]:
            result = translate("test", lang)
            assert "翻译结果" in result


class TestSearchKnowledge:
    """Tests for the search_knowledge tool."""

    def test_rust_query(self):
        result = search_knowledge("Rust")
        assert "Rust" in result

    def test_agent_query(self):
        result = search_knowledge("Agent")
        assert "Agent" in result or "agent" in result

    def test_no_results(self):
        result = search_knowledge("xyznonexistent123")
        assert "未找到" in result

    def test_max_results(self):
        result = search_knowledge("编程语言", max_results=1)
        # Should return at most 1 result
        assert result.count("[1]") <= 1

    def test_python_query(self):
        result = search_knowledge("Python")
        assert "Python" in result


class TestToolRegistry:
    """Tests for the tool registry."""

    def test_create_default_registry(self):
        registry = create_default_registry()
        assert len(registry.names) >= 5
        assert "get_weather" in registry.names
        assert "calculate" in registry.names
        assert "get_current_time" in registry.names
        assert "translate" in registry.names
        assert "search_knowledge" in registry.names

    def test_execute_known_tool(self):
        registry = create_default_registry()
        result = registry.execute("calculate", {"expression": "1 + 1"})
        assert "2" in result

    def test_execute_unknown_tool(self):
        registry = create_default_registry()
        result = registry.execute("nonexistent_tool", {})
        assert "Error" in result or "Unknown" in result

    def test_list_tools(self):
        registry = create_default_registry()
        tools = registry.list_tools()
        assert len(tools) >= 5
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
