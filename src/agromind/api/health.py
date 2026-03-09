"""GET /health — liveness probe."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

_VERSION = "0.1.0"


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": _VERSION}
