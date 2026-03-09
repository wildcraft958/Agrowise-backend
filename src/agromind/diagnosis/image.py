"""Image loading, validation, and base64 encoding for diagnosis pipeline."""

from __future__ import annotations

import base64
from pathlib import Path


def load_image_bytes(path: str) -> bytes:
    """Load image from disk as bytes.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return p.read_bytes()


def validate_image(data: bytes, max_bytes: int = 5 * 1024 * 1024) -> dict:
    """Validate image bytes for size and format.

    Returns:
        Dict with keys: valid (bool), format (str), size_bytes (int), reason (str).
    """
    size = len(data)

    if size == 0:
        return {"valid": False, "format": "unknown", "size_bytes": 0, "reason": "empty data"}

    if size > max_bytes:
        return {
            "valid": False,
            "format": "unknown",
            "size_bytes": size,
            "reason": f"size {size} exceeds {max_bytes} byte limit",
        }

    fmt = _detect_format(data)
    return {"valid": True, "format": fmt, "size_bytes": size, "reason": ""}


def encode_base64(data: bytes) -> str:
    """Encode bytes as a base64 string. Returns '' for empty input."""
    if not data:
        return ""
    return base64.b64encode(data).decode("ascii")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _detect_format(data: bytes) -> str:
    if data[:2] == b"\xff\xd8":
        return "JPEG"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if data[:4] in (b"GIF8", b"GIF9"):
        return "GIF"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return "unknown"
