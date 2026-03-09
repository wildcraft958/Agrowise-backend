"""Tests that ChatVertexAI and VertexAIEmbeddings initialize with config values."""

from unittest.mock import patch


def test_chat_vertexai_uses_config():
    """ChatVertexAI is constructed with model/project/location from config."""
    with patch("langchain_google_vertexai.ChatVertexAI.__init__", return_value=None) as mock_init:
        from langchain_google_vertexai import ChatVertexAI

        from agromind.config import settings

        ChatVertexAI(
            model_name=settings.models.chat,
            project=settings.gcp.project_id,
            location=settings.gcp.location,
            temperature=settings.models.temperature,
            max_output_tokens=settings.models.max_output_tokens,
        )

        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model_name"] == "gemini-2.5-flash"
        assert call_kwargs["project"] == "agrowise-192e3"
        assert call_kwargs["location"] == "us-central1"
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_output_tokens"] == 2048


def test_vertexai_embeddings_uses_config():
    """VertexAIEmbeddings is constructed with embedding model/project/location from config."""
    target = "langchain_google_vertexai.VertexAIEmbeddings.__init__"
    with patch(target, return_value=None) as mock_init:
        from langchain_google_vertexai import VertexAIEmbeddings

        from agromind.config import settings

        VertexAIEmbeddings(
            model_name=settings.models.embedding,
            project=settings.gcp.project_id,
            location=settings.gcp.location,
        )

        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model_name"] == "text-embedding-005"
        assert call_kwargs["project"] == "agrowise-192e3"


def test_model_switch_via_env(monkeypatch):
    """Switching model via env var is reflected in settings."""
    monkeypatch.setenv("AGRO_MODELS__CHAT", "gemini-2.5-pro")
    from agromind.config import Settings
    s = Settings.from_yaml("config.yaml")
    assert s.models.chat == "gemini-2.5-pro"
