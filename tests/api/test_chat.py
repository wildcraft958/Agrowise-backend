"""Tests for POST /agromind/chat — api/chat.py."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agromind.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


_MOCK_AGENT_RESPONSE = {
    "answer": "Apply 120 kg/ha urea at tillering stage.",
    "tool_trace": ["cibrc_safety_check", "imd_weather_check"],
    "safety_violation": False,
    "violations": [],
}


class TestChatEndpoint:
    def test_returns_200_with_valid_body(self, client):
        with patch("agromind.api.chat._agent") as mock_agent:
            mock_agent.invoke.return_value = _MOCK_AGENT_RESPONSE
            response = client.post(
                "/agromind/chat",
                json={"message": "How much urea for wheat?", "user_id": "u1"},
            )
        assert response.status_code == 200

    def test_response_has_answer(self, client):
        with patch("agromind.api.chat._agent") as mock_agent:
            mock_agent.invoke.return_value = _MOCK_AGENT_RESPONSE
            response = client.post(
                "/agromind/chat",
                json={"message": "Fertilizer for rice?", "user_id": "u1"},
            )
        data = response.json()
        assert "answer" in data

    def test_response_has_tool_trace(self, client):
        with patch("agromind.api.chat._agent") as mock_agent:
            mock_agent.invoke.return_value = _MOCK_AGENT_RESPONSE
            response = client.post(
                "/agromind/chat",
                json={"message": "Pest on wheat?", "user_id": "u1"},
            )
        data = response.json()
        assert "tool_trace" in data

    def test_missing_message_returns_422(self, client):
        response = client.post("/agromind/chat", json={"user_id": "u1"})
        assert response.status_code == 422

    def test_safety_violation_flagged_in_response(self, client):
        violation_response = {**_MOCK_AGENT_RESPONSE, "safety_violation": True, "violations": ["Aldrin"]}
        with patch("agromind.api.chat._agent") as mock_agent:
            mock_agent.invoke.return_value = violation_response
            response = client.post(
                "/agromind/chat",
                json={"message": "Use Aldrin for pests?", "user_id": "u1"},
            )
        data = response.json()
        assert data.get("safety_violation") is True
