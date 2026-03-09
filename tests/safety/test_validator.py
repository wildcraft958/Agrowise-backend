"""Tests for SafetyValidator — safety/validator.py."""

import pytest

from agromind.safety.validator import SafetyValidator


BANNED = {"DDT", "Aldrin", "Endrin", "Chlordane", "Dicofol"}


@pytest.fixture
def validator():
    return SafetyValidator(banned_chemicals=BANNED, strict_mode=True)


@pytest.fixture
def lenient():
    return SafetyValidator(banned_chemicals=BANNED, strict_mode=False)


class TestSafetyValidatorInit:
    def test_instantiates(self):
        v = SafetyValidator(banned_chemicals=BANNED)
        assert v is not None


class TestScan:
    def test_clean_text_returns_empty(self, validator):
        result = validator.scan("Apply neem oil spray on wheat.")
        assert result == []

    def test_detects_banned_chemical(self, validator):
        result = validator.scan("You can use DDT for pest control.")
        assert "DDT" in result

    def test_case_insensitive_detection(self, validator):
        result = validator.scan("Apply ddt to the field.")
        assert len(result) > 0

    def test_detects_multiple_banned(self, validator):
        result = validator.scan("Use DDT and Aldrin together.")
        assert "DDT" in result
        assert "Aldrin" in result

    def test_partial_word_not_flagged(self, validator):
        # "Aldrington" should not match "Aldrin"
        result = validator.scan("Visit Aldrington farm.")
        assert result == []


class TestValidate:
    def test_clean_text_passes(self, validator):
        result = validator.validate("Apply urea at 120 kg/ha.")
        assert result["safe"] is True
        assert result["violations"] == []

    def test_banned_chemical_strict_mode(self, validator):
        result = validator.validate("Use DDT for cotton pests.")
        assert result["safe"] is False
        assert "DDT" in result["violations"]

    def test_banned_chemical_lenient_mode(self, lenient):
        result = lenient.validate("Use DDT for cotton pests.")
        assert result["safe"] is False
        assert result.get("strict") is False  # lenient mode, not strict

    def test_result_has_required_keys(self, validator):
        result = validator.validate("Some text here.")
        assert "safe" in result
        assert "violations" in result

    def test_empty_text_is_safe(self, validator):
        result = validator.validate("")
        assert result["safe"] is True
