"""Tests for SarvamTTS — voice/tts.py."""

from unittest.mock import patch

import pytest

from agromind.voice.tts import SarvamTTS


@pytest.fixture
def tts():
    return SarvamTTS(api_key="test-key", language="hi")


class TestSarvamTTSInit:
    def test_instantiates(self):
        client = SarvamTTS(api_key="key", language="hi")
        assert client is not None

    def test_stores_language(self):
        client = SarvamTTS(api_key="key", language="od")
        assert client.language == "od"

    def test_default_language_hindi(self):
        client = SarvamTTS(api_key="key")
        assert client.language == "hi"


class TestSynthesize:
    def test_returns_bytes(self, tts):
        with patch.object(tts, "_post") as mock_post:
            mock_post.return_value = b"\xff\xfb\x90\x00" * 100  # fake MP3
            result = tts.synthesize("गेहूँ में पानी देना जरूरी है।")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_language_override(self, tts):
        with patch.object(tts, "_post") as mock_post:
            mock_post.return_value = b"audio"
            tts.synthesize("hello", language="en")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs.get("language") == "en"

    def test_api_error_returns_empty_bytes(self, tts):
        with patch.object(tts, "_post", side_effect=RuntimeError("Sarvam down")):
            result = tts.synthesize("test")
        assert result == b""

    def test_empty_text_returns_empty_bytes(self, tts):
        result = tts.synthesize("")
        assert result == b""
