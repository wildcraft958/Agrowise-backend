"""POST /diagnosis — crop disease image diagnosis endpoint."""
from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agromind.diagnosis.detector import DiseaseDetector

router = APIRouter()

_detector = DiseaseDetector()


class DiagnosisRequest(BaseModel):
    image_b64: str
    crop: str | None = None
    user_id: str


@router.post("/diagnosis")
async def diagnose(body: DiagnosisRequest) -> dict:
    """Diagnose a crop disease from a base64-encoded image."""
    try:
        image_bytes = base64.b64decode(body.image_b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data") from exc

    result = _detector.diagnose(image_bytes, crop=body.crop)
    return result
