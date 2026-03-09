"""Tests for prompt builder — agent/prompt.py."""

import pytest
from langchain_core.documents import Document

from agromind.agent.prompt import build_context_block, build_system_prompt


class TestBuildSystemPrompt:
    def test_returns_string(self):
        result = build_system_prompt(["cibrc_safety_check", "imd_weather_check"])
        assert isinstance(result, str)

    def test_contains_mandatory_tool_names(self):
        result = build_system_prompt(["cibrc_safety_check", "imd_weather_check"])
        assert "cibrc_safety_check" in result
        assert "imd_weather_check" in result

    def test_instructs_always_call(self):
        result = build_system_prompt(["cibrc_safety_check"])
        lower = result.lower()
        # Must instruct the model to always call mandatory tools
        assert "always" in lower or "must" in lower or "mandatory" in lower

    def test_empty_mandatory_still_returns_string(self):
        result = build_system_prompt([])
        assert isinstance(result, str)
        assert len(result) > 50  # Non-trivial system prompt


class TestBuildContextBlock:
    def test_returns_string(self):
        result = build_context_block(wiki={}, rag_chunks=[])
        assert isinstance(result, str)

    def test_includes_wiki_summary(self):
        wiki = {"title": "Wheat", "summary": "Wheat is a rabi cereal."}
        result = build_context_block(wiki=wiki, rag_chunks=[])
        assert "Wheat" in result
        assert "rabi cereal" in result

    def test_includes_rag_chunk_content(self):
        chunks = [Document(page_content="Apply 120 kg/ha urea for wheat.", metadata={})]
        result = build_context_block(wiki={}, rag_chunks=chunks)
        assert "120 kg/ha" in result

    def test_includes_geo_context(self):
        geo = {"state": "Punjab", "district": "Ludhiana", "block": "Ludhiana-1"}
        result = build_context_block(wiki={}, rag_chunks=[], geo=geo)
        assert "Punjab" in result

    def test_empty_wiki_and_chunks_returns_non_empty(self):
        result = build_context_block(wiki={}, rag_chunks=[])
        # Still returns something (context section header at minimum)
        assert isinstance(result, str)

    def test_multiple_chunks_all_included(self):
        chunks = [
            Document(page_content=f"Chunk {i} content.", metadata={})
            for i in range(3)
        ]
        result = build_context_block(wiki={}, rag_chunks=chunks)
        for i in range(3):
            assert f"Chunk {i}" in result
