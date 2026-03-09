"""Sarvam AI Text-to-Speech (TTS) client.

API endpoint: POST https://api.sarvam.ai/text-to-speech
Sends text and returns MP3 audio bytes in the requested language.

Returns b"" on error so callers can degrade gracefully (text-only response).
"""

from __future__ import annotations

import base64
import logging

import httpx

logger = logging.getLogger(__name__)

_TTS_URL = "https://api.sarvam.ai/text-to-speech"


class SarvamTTS:
    """Sarvam AI text-to-speech client."""

    def __init__(self, api_key: str, language: str = "hi") -> None:
        self.language = language
        self._api_key = api_key

    def synthesize(self, text: str, language: str | None = None) -> bytes:
        """Convert text to speech audio bytes.

        Args:
            text: Text to synthesize.
            language: BCP-47 language code override (e.g. "en", "hi").

        Returns:
            MP3 audio bytes, or b"" on error or empty input.
        """
        if not text.strip():
            return b""

        lang = language or self.language
        try:
            return self._post(text=text, language=lang)
        except Exception as exc:
            logger.warning("SarvamTTS error: %s", exc)
            return b""

    def _post(self, text: str, language: str) -> bytes:
        """Send request to Sarvam TTS API and return audio bytes."""
        response = httpx.post(
            _TTS_URL,
            headers={"api-subscription-key": self._api_key, "Content-Type": "application/json"},
            json={
                "inputs": [text],
                "target_language_code": language,
                "speaker": "meera",
                "model": "bulbul:v1",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        # Sarvam returns base64-encoded audio in audios[0]
        audio_b64 = data.get("audios", [""])[0]
        return base64.b64decode(audio_b64) if audio_b64 else b""
