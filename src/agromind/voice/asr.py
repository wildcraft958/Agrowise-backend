"""Sarvam AI Speech-to-Text (ASR) client.

API endpoint: POST https://api.sarvam.ai/speech-to-text
Sends WAV/MP3 audio and returns a transcript in the requested language.

Supported languages: en, hi, bn, od (and other Indic languages supported by Sarvam).
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_ASR_URL = "https://api.sarvam.ai/speech-to-text"


class SarvamASR:
    """Sarvam AI speech-to-text client."""

    def __init__(self, api_key: str, language: str = "hi") -> None:
        self.language = language
        self._api_key = api_key

    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> dict:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio bytes (WAV or MP3).
            language: BCP-47 language code override (e.g. "en", "hi").

        Returns:
            Dict with "transcript" key, or {"error": ...} on failure.
        """
        if not audio_bytes:
            return {"error": "empty audio", "transcript": ""}

        lang = language or self.language
        try:
            return self._post(audio_bytes=audio_bytes, language=lang)
        except Exception as exc:
            logger.warning("SarvamASR error: %s", exc)
            return {"error": str(exc), "transcript": ""}

    def _post(self, audio_bytes: bytes, language: str) -> dict:
        """Send request to Sarvam ASR API."""
        response = httpx.post(
            _ASR_URL,
            headers={"api-subscription-key": self._api_key},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"language_code": language, "model": "saarika:v2"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return {"transcript": data.get("transcript", ""), **data}
