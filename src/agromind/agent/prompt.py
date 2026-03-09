"""System prompt and context injection stub."""
from __future__ import annotations


def build_system_prompt(mandatory_tool_names: list[str]) -> str:
    raise NotImplementedError


def build_context_block(
    wiki: dict,
    rag_chunks: list,
    geo: dict | None = None,
) -> str:
    raise NotImplementedError
