"""Mandatory tool enforcement utilities.

After the agent produces a response, inspect the message history to verify
that all mandatory tools were called. Return which ones are missing so the
caller can retry or reject.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage


def get_called_tool_names(messages: list[BaseMessage]) -> list[str]:
    """Return deduplicated list of tool names called across all AIMessages."""
    seen: set[str] = set()
    for msg in messages:
        if isinstance(msg, AIMessage):
            for tc in getattr(msg, "tool_calls", []) or []:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if name:
                    seen.add(name)
    return list(seen)


def missing_mandatory_tools(
    messages: list[BaseMessage],
    mandatory: list[str],
) -> list[str]:
    """Return mandatory tools that were NOT called in the message history."""
    if not mandatory:
        return []
    called = set(get_called_tool_names(messages))
    return [t for t in mandatory if t not in called]
