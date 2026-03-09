"""Tests for config loading — YAML defaults and env overrides."""

import pytest

from agromind.config import Settings


def test_yaml_defaults_load():
    """Config loads from config.yaml with expected defaults."""
    s = Settings.from_yaml("config.yaml")
    assert s.gcp.project_id == "agrowise-192e3"
    assert s.gcp.location == "us-central1"
    assert s.models.chat == "gemini-2.5-flash"
    assert s.models.embedding == "text-embedding-005"
    assert s.models.temperature == 0.2
    assert s.rag.top_k == 5
    assert s.rag.collections["icar"] == "icar_knowledge"
    assert s.rag.collections["kcc"] == "kcc_transcripts"
    assert s.safety.strict_mode is True
    assert "cibrc_safety_check" in s.tools.mandatory
    assert "imd_weather_check" in s.tools.mandatory
    assert s.firebase.enabled is True


def test_missing_yaml_uses_defaults():
    """When config.yaml is absent, hardcoded defaults apply."""
    s = Settings.from_yaml("nonexistent.yaml")
    assert s.gcp.project_id == "agrowise-192e3"
    assert s.models.chat == "gemini-2.5-flash"


def test_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch):
    """Env vars override YAML values."""
    monkeypatch.setenv("AGRO_MODELS__CHAT", "gemini-2.5-pro")
    monkeypatch.setenv("AGRO_GCP__PROJECT_ID", "other-project")
    s = Settings.from_yaml("config.yaml")
    assert s.models.chat == "gemini-2.5-pro"
    assert s.gcp.project_id == "other-project"


def test_secrets_from_env_only(monkeypatch: pytest.MonkeyPatch):
    """Secrets default to empty string; can be set via env."""
    monkeypatch.setenv("AGRO_SARVAM_API_KEY", "test-key-123")
    s = Settings.from_yaml("config.yaml")
    assert s.sarvam_api_key == "test-key-123"


def test_geo_csv_paths():
    """Geo CSV paths reference bolbhav-data files."""
    s = Settings.from_yaml("config.yaml")
    assert "Location hierarchy.csv" in s.geo.location_hierarchy_csv
    assert "District Neighbour Map India.csv" in s.geo.neighbour_map_csv
    assert "IMD Agromet advisory locations.csv" in s.geo.imd_stations_csv
