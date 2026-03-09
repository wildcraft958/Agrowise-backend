"""Disease detector using Gemini vision via Vertex AI.

Sends a base64-encoded crop image to Gemini along with a structured prompt.
The model returns a JSON diagnosis with disease name, confidence, and recommendations.

If the model returns non-JSON text, it is returned as {"raw": ...} rather than crashing.
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agromind.config import settings
from agromind.diagnosis.image import encode_base64

logger = logging.getLogger(__name__)

_DIAGNOSIS_PROMPT = """\
You are an agricultural plant disease expert. Analyze this crop image and respond
with a JSON object only (no markdown, no extra text) in this exact format:
{{
  "disease": "<disease name or 'Healthy' if no disease>",
  "confidence": <float 0.0-1.0>,
  "severity": "<None|Mild|Moderate|Severe>",
  "affected_area_pct": <estimated % of visible area affected, 0-100>,
  "recommendations": ["<action 1>", "<action 2>"],
  "additional_notes": "<any relevant observation>"
}}
{crop_hint}
"""


class DiseaseDetector:
    """Gemini vision-based crop disease detector."""

    def __init__(self) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model=settings.models.vision,
            vertexai=True,
            project=settings.gcp.project_id,
            location=settings.gcp.location,
            temperature=0.1,  # deterministic for diagnosis
            max_output_tokens=512,
        )

    def diagnose(self, image_bytes: bytes, crop: str | None = None) -> dict:
        """Diagnose disease from crop image bytes.

        Args:
            image_bytes: Raw image bytes (JPEG/PNG).
            crop: Optional crop type hint (e.g. "wheat", "rice").

        Returns:
            Dict with disease, confidence, severity, recommendations.
            Returns {"error": ...} on LLM failure.
            Returns {"raw": ..., "disease": "unknown"} on non-JSON response.
        """
        crop_hint = f"The crop in the image is: {crop}." if crop else ""
        prompt_text = _DIAGNOSIS_PROMPT.format(crop_hint=crop_hint)
        b64 = encode_base64(image_bytes)

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
            ]
        )

        try:
            response = self._llm.invoke([message])
            raw_text = response.content.strip()
        except Exception as exc:
            logger.error("DiseaseDetector LLM error: %s", exc)
            return {"error": str(exc)}

        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, ValueError):
            logger.warning("DiseaseDetector: non-JSON response: %s", raw_text[:200])
            return {"raw": raw_text, "disease": "unknown", "confidence": 0.0,
                    "recommendations": []}
