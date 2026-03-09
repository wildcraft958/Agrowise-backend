"""Tests for POST /diagnosis — api/diagnosis.py."""

import base64
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agromind.main import app

_FAKE_JPEG_B64 = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 20 + b"\xff\xd9").decode()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


_MOCK_DIAGNOSIS = {
    "disease": "Yellow Rust",
    "confidence": 0.87,
    "severity": "Moderate",
    "recommendations": ["Apply propiconazole fungicide."],
}


class TestDiagnosisEndpoint:
    def test_returns_200_with_valid_body(self, client):
        with patch("agromind.api.diagnosis._detector") as mock_det:
            mock_det.diagnose.return_value = _MOCK_DIAGNOSIS
            response = client.post(
                "/diagnosis",
                json={"image_b64": _FAKE_JPEG_B64, "crop": "wheat", "user_id": "u1"},
            )
        assert response.status_code == 200

    def test_response_has_disease(self, client):
        with patch("agromind.api.diagnosis._detector") as mock_det:
            mock_det.diagnose.return_value = _MOCK_DIAGNOSIS
            response = client.post(
                "/diagnosis",
                json={"image_b64": _FAKE_JPEG_B64, "crop": "wheat", "user_id": "u1"},
            )
        data = response.json()
        assert "disease" in data

    def test_missing_image_returns_422(self, client):
        response = client.post("/diagnosis", json={"crop": "wheat", "user_id": "u1"})
        assert response.status_code == 422

    def test_invalid_base64_returns_400(self, client):
        response = client.post(
            "/diagnosis",
            json={"image_b64": "not-valid-base64!!!", "crop": "wheat", "user_id": "u1"},
        )
        assert response.status_code == 400
