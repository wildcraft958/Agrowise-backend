"""Tests for SarvamASR — voice/asr.py."""

from unittest.mock import MagicMock, patch

import pytest

from agromind.voice.asr import SarvamASR

_FAKE_WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 20


@pytest.fixture
def asr():
    return SarvamASR(api_key="test-key", language="hi")


class TestSarvamASRInit:
    def test_instantiates(self):
        client = SarvamASR(api_key="key", language="hi")
        assert client is not None

    def test_stores_language(self):
        client = SarvamASR(api_key="key", language="bn")
        assert client.language == "bn"

    def test_default_language_hindi(self):
        client = SarvamASR(api_key="key")
        assert client.language == "hi"


class TestTranscribe:
    def test_returns_dict(self, asr):
        with patch.object(asr, "_post") as mock_post:
            mock_post.return_value = {"transcript": "गेहूँ में कीट लगे हैं"}
            result = asr.transcribe(_FAKE_WAV)
        assert isinstance(result, dict)

    def test_has_transcript_key(self, asr):
        with patch.object(asr, "_post") as mock_post:
            mock_post.return_value = {"transcript": "wheat pest problem"}
            result = asr.transcribe(_FAKE_WAV)
        assert "transcript" in result

    def test_language_override(self, asr):
        with patch.object(asr, "_post") as mock_post:
            mock_post.return_value = {"transcript": "test"}
            asr.transcribe(_FAKE_WAV, language="en")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs.get("language") == "en"

    def test_api_error_returns_error_dict(self, asr):
        with patch.object(asr, "_post", side_effect=RuntimeError("API down")):
            result = asr.transcribe(_FAKE_WAV)
        assert "error" in result

    def test_empty_audio_returns_error(self, asr):
        result = asr.transcribe(b"")
        assert "error" in result
