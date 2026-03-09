"""Tests that ChatGoogleGenerativeAI and VertexAIEmbeddings initialize with config values."""

from unittest.mock import patch


def test_chat_google_genai_uses_config():
    """ChatGoogleGenerativeAI is constructed with model/project/location from config."""
    target = "langchain_google_genai.ChatGoogleGenerativeAI.__init__"
    with patch(target, return_value=None) as mock_init:
        from langchain_google_genai import ChatGoogleGenerativeAI

        from agromind.config import settings

        ChatGoogleGenerativeAI(
            model=settings.models.chat,
            vertexai=True,
            project=settings.gcp.project_id,
            location=settings.gcp.location,
            temperature=settings.models.temperature,
            max_output_tokens=settings.models.max_output_tokens,
        )

        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.5-flash"
        assert call_kwargs["vertexai"] is True
        assert call_kwargs["project"] == "agrowise-192e3"
        assert call_kwargs["location"] == "us-central1"
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_output_tokens"] == 2048


def test_genai_embeddings_uses_config():
    """GoogleGenerativeAIEmbeddings is constructed with embedding model/project/location from config."""
    target = "langchain_google_genai.GoogleGenerativeAIEmbeddings.__init__"
    with patch(target, return_value=None) as mock_init:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        from agromind.config import settings

        GoogleGenerativeAIEmbeddings(
            model=settings.models.embedding,
            project=settings.gcp.project_id,
            location=settings.gcp.location,
        )

        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args.kwargs
        assert call_kwargs["model"] == "text-embedding-005"
        assert call_kwargs["project"] == "agrowise-192e3"


def test_model_switch_via_env(monkeypatch):
    """Switching model via env var is reflected in settings."""
    monkeypatch.setenv("AGRO_MODELS__CHAT", "gemini-2.5-pro")
    from agromind.config import Settings
    s = Settings.from_yaml("config.yaml")
    assert s.models.chat == "gemini-2.5-pro"
