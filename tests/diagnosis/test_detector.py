"""Tests for DiseaseDetector — diagnosis/detector.py."""

from unittest.mock import MagicMock, patch

import pytest

from agromind.diagnosis.detector import DiseaseDetector

_FAKE_IMAGE = b"\xff\xd8\xff\xe0" + b"\x00" * 20 + b"\xff\xd9"


@pytest.fixture
def detector():
    with patch("agromind.diagnosis.detector.ChatGoogleGenerativeAI"):
        return DiseaseDetector()


class TestDiseaseDetectorInit:
    def test_instantiates(self):
        with patch("agromind.diagnosis.detector.ChatGoogleGenerativeAI"):
            d = DiseaseDetector()
        assert d is not None

    def test_uses_vision_model_from_config(self):
        from agromind.config import settings
        with patch("agromind.diagnosis.detector.ChatGoogleGenerativeAI") as MockLLM:
            DiseaseDetector()
            kwargs = MockLLM.call_args[1]
            assert kwargs.get("model") == settings.models.vision


class TestDiagnose:
    def test_returns_dict(self, detector):
        mock_response = MagicMock()
        mock_response.content = '{"disease": "Yellow Rust", "confidence": 0.87, "recommendations": ["Apply fungicide"]}'
        with patch.object(detector, "_llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response
            result = detector.diagnose(_FAKE_IMAGE, crop="wheat")
        assert isinstance(result, dict)

    def test_result_has_disease_key(self, detector):
        mock_response = MagicMock()
        mock_response.content = '{"disease": "Brown Rust", "confidence": 0.75, "recommendations": []}'
        with patch.object(detector, "_llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response
            result = detector.diagnose(_FAKE_IMAGE)
        assert "disease" in result

    def test_result_has_confidence_key(self, detector):
        mock_response = MagicMock()
        mock_response.content = '{"disease": "Brown Rust", "confidence": 0.75, "recommendations": []}'
        with patch.object(detector, "_llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response
            result = detector.diagnose(_FAKE_IMAGE)
        assert "confidence" in result

    def test_result_has_recommendations(self, detector):
        mock_response = MagicMock()
        mock_response.content = '{"disease": "Leaf Blight", "confidence": 0.9, "recommendations": ["Remove infected leaves"]}'
        with patch.object(detector, "_llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response
            result = detector.diagnose(_FAKE_IMAGE, crop="rice")
        assert "recommendations" in result

    def test_llm_error_returns_error_dict(self, detector):
        with patch.object(detector, "_llm") as mock_llm:
            mock_llm.invoke.side_effect = RuntimeError("Vertex AI timeout")
            result = detector.diagnose(_FAKE_IMAGE)
        assert "error" in result

    def test_invalid_json_returns_raw_text(self, detector):
        mock_response = MagicMock()
        mock_response.content = "This plant looks healthy."
        with patch.object(detector, "_llm") as mock_llm:
            mock_llm.invoke.return_value = mock_response
            result = detector.diagnose(_FAKE_IMAGE)
        # Should not crash — returns something usable
        assert isinstance(result, dict)
