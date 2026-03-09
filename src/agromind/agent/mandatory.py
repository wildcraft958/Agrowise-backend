"""Mandatory tool enforcement stub."""
from __future__ import annotations

from langchain_core.messages import BaseMessage


def get_called_tool_names(messages: list[BaseMessage]) -> list[str]:
    raise NotImplementedError


def missing_mandatory_tools(
    messages: list[BaseMessage],
    mandatory: list[str],
) -> list[str]:
    raise NotImplementedError
