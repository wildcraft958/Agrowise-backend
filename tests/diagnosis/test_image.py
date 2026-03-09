"""Tests for image preprocessing — diagnosis/image.py."""

import base64
from pathlib import Path

import pytest

from agromind.diagnosis.image import encode_base64, load_image_bytes, validate_image

# Minimal valid JPEG bytes (SOI + EOI markers)
_TINY_JPEG = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * 10 + bytes([0xFF, 0xD9])
_TINY_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


class TestLoadImageBytes:
    def test_loads_existing_file(self, tmp_path):
        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(_TINY_JPEG)
        data = load_image_bytes(str(img_file))
        assert isinstance(data, bytes)
        assert len(data) == len(_TINY_JPEG)

    def test_raises_for_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_image_bytes("/no/such/file.jpg")


class TestValidateImage:
    def test_valid_jpeg_passes(self):
        result = validate_image(_TINY_JPEG)
        assert result["valid"] is True
        assert result["format"] in ("JPEG", "jpeg", "jpg")

    def test_valid_png_passes(self):
        result = validate_image(_TINY_PNG)
        assert result["valid"] is True

    def test_oversized_image_fails(self):
        big = b"x" * (6 * 1024 * 1024)
        result = validate_image(big, max_bytes=5 * 1024 * 1024)
        assert result["valid"] is False
        assert "size" in result.get("reason", "").lower()

    def test_empty_bytes_fails(self):
        result = validate_image(b"")
        assert result["valid"] is False

    def test_result_has_size_key(self):
        result = validate_image(_TINY_JPEG)
        assert "size_bytes" in result


class TestEncodeBase64:
    def test_returns_string(self):
        result = encode_base64(b"hello world")
        assert isinstance(result, str)

    def test_is_valid_base64(self):
        result = encode_base64(b"hello world")
        decoded = base64.b64decode(result)
        assert decoded == b"hello world"

    def test_empty_bytes(self):
        result = encode_base64(b"")
        assert result == ""
