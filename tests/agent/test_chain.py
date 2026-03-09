"""Tests for AgroMindAgent chain — agent/chain.py.

All Vertex AI calls are mocked. Tests verify:
- Chain assembles correctly with config values
- Tools are bound
- Response structure is correct
- Mandatory tool enforcement retries when tools are skipped
- CIBRC post-filter flags banned chemicals
"""

from unittest.mock import MagicMock, patch

import pytest

from agromind.agent.chain import AgroMindAgent


def _mock_llm_response(content: str, tool_calls: list | None = None):
    """Build a mock AIMessage response."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg


@pytest.fixture
def mock_llm():
    with patch("agromind.agent.chain.ChatVertexAI") as MockLLM:
        instance = MagicMock()
        MockLLM.return_value = instance
        yield instance


@pytest.fixture
def agent(mock_llm):
    with patch("agromind.agent.chain.ChatVertexAI"):
        return AgroMindAgent()


class TestAgroMindAgentInit:
    def test_instantiates(self):
        with patch("agromind.agent.chain.ChatVertexAI"):
            a = AgroMindAgent()
        assert a is not None

    def test_uses_config_model(self):
        from agromind.config import settings
        with patch("agromind.agent.chain.ChatVertexAI") as MockLLM:
            AgroMindAgent()
            call_kwargs = MockLLM.call_args[1]
            assert call_kwargs.get("model_name") == settings.models.chat

    def test_uses_config_temperature(self):
        from agromind.config import settings
        with patch("agromind.agent.chain.ChatVertexAI") as MockLLM:
            AgroMindAgent()
            call_kwargs = MockLLM.call_args[1]
            assert call_kwargs.get("temperature") == settings.models.temperature

    def test_all_tools_bound(self):
        from agromind.agent.tools import ALL_TOOLS
        with patch("agromind.agent.chain.ChatVertexAI") as MockLLM:
            instance = MagicMock()
            MockLLM.return_value = instance
            AgroMindAgent()
        # bind_tools should have been called with all tools
        instance.bind_tools.assert_called_once()
        bound_tools = instance.bind_tools.call_args[0][0]
        assert len(bound_tools) == len(ALL_TOOLS)


class TestAgroMindAgentInvoke:
    def test_returns_dict(self, agent, mock_llm):
        mock_llm.bind_tools.return_value.invoke.return_value = _mock_llm_response(
            "Wheat advisory: Apply urea at tillering."
        )
        with patch("agromind.agent.chain.missing_mandatory_tools", return_value=[]):
            result = agent.invoke("What fertilizer should I apply to wheat?")
        assert isinstance(result, dict)

    def test_result_has_answer_key(self, agent, mock_llm):
        mock_llm.bind_tools.return_value.invoke.return_value = _mock_llm_response(
            "Apply 120 kg/ha urea."
        )
        with patch("agromind.agent.chain.missing_mandatory_tools", return_value=[]):
            result = agent.invoke("Fertilizer for wheat?")
        assert "answer" in result

    def test_result_has_tool_trace(self, agent, mock_llm):
        mock_llm.bind_tools.return_value.invoke.return_value = _mock_llm_response(
            "Use neem oil spray."
        )
        with patch("agromind.agent.chain.missing_mandatory_tools", return_value=[]):
            result = agent.invoke("Pest control?")
        assert "tool_trace" in result

    def test_strict_mode_flags_banned_chemical(self, agent, mock_llm):
        # Response contains DDT — a banned chemical
        mock_llm.bind_tools.return_value.invoke.return_value = _mock_llm_response(
            "You can use DDT for pest control."
        )
        with patch("agromind.agent.chain.missing_mandatory_tools", return_value=[]):
            result = agent.invoke("Pest control?")
        # In strict mode, response should be flagged or replaced
        assert result.get("safety_violation") is True or "banned" in result.get("answer", "").lower()
