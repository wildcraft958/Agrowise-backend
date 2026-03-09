"""Tests for mandatory tool enforcement — agent/mandatory.py."""

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from agromind.agent.mandatory import get_called_tool_names, missing_mandatory_tools


def _ai_with_tool_calls(*tool_names: str) -> AIMessage:
    """Build an AIMessage that records tool calls."""
    tool_calls = [
        {"name": name, "args": {}, "id": f"call_{i}", "type": "tool_call"}
        for i, name in enumerate(tool_names)
    ]
    return AIMessage(content="", tool_calls=tool_calls)


class TestGetCalledToolNames:
    def test_extracts_tool_names_from_ai_message(self):
        msgs = [_ai_with_tool_calls("cibrc_safety_check", "imd_weather_check")]
        names = get_called_tool_names(msgs)
        assert "cibrc_safety_check" in names
        assert "imd_weather_check" in names

    def test_empty_messages_returns_empty(self):
        assert get_called_tool_names([]) == []

    def test_no_tool_calls_returns_empty(self):
        msgs = [AIMessage(content="No tools used.")]
        assert get_called_tool_names(msgs) == []

    def test_deduplicates_repeated_calls(self):
        msgs = [_ai_with_tool_calls("cibrc_safety_check", "cibrc_safety_check")]
        names = get_called_tool_names(msgs)
        assert names.count("cibrc_safety_check") == 1

    def test_multiple_ai_messages(self):
        msgs = [
            _ai_with_tool_calls("cibrc_safety_check"),
            _ai_with_tool_calls("imd_weather_check"),
        ]
        names = get_called_tool_names(msgs)
        assert "cibrc_safety_check" in names
        assert "imd_weather_check" in names


class TestMissingMandatoryTools:
    def test_all_called_returns_empty(self):
        msgs = [_ai_with_tool_calls("cibrc_safety_check", "imd_weather_check")]
        missing = missing_mandatory_tools(msgs, ["cibrc_safety_check", "imd_weather_check"])
        assert missing == []

    def test_one_missing_returns_it(self):
        msgs = [_ai_with_tool_calls("cibrc_safety_check")]
        missing = missing_mandatory_tools(msgs, ["cibrc_safety_check", "imd_weather_check"])
        assert "imd_weather_check" in missing

    def test_none_called_returns_all_mandatory(self):
        msgs = [AIMessage(content="Hello")]
        missing = missing_mandatory_tools(msgs, ["cibrc_safety_check", "imd_weather_check"])
        assert set(missing) == {"cibrc_safety_check", "imd_weather_check"}

    def test_empty_mandatory_always_empty(self):
        msgs = [_ai_with_tool_calls("some_tool")]
        assert missing_mandatory_tools(msgs, []) == []
