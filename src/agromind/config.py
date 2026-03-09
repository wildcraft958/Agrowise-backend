"""
Centralized configuration for AgroMind backend.

Loads from config.yaml (defaults, model selection, feature toggles)
with environment variable overrides for secrets.

Usage:
    from agromind.config import settings
    llm = ChatGoogleGenerativeAI(
        model=settings.models.chat,
        vertexai=True,
        project=settings.gcp.project_id,
        location=settings.gcp.location,
        temperature=settings.models.temperature,
    )
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


class GCPConfig(BaseModel):
    project_id: str = "agrowise-192e3"
    location: str = "us-central1"
    storage_bucket: str = "agrowise-192e3.firebasestorage.app"


class ModelsConfig(BaseModel):
    chat: str = "gemini-2.5-flash"
    vision: str = "gemini-2.5-flash"
    embedding: str = "text-embedding-005"
    temperature: float = 0.2
    max_output_tokens: int = 2048


class RAGConfig(BaseModel):
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    chroma_persist_dir: str = "./chroma_db"
    collections: dict[str, str] = {"icar": "icar_knowledge", "kcc": "kcc_transcripts"}


class SafetyConfig(BaseModel):
    cibrc_csv_path: str = "data/cibrc_database.csv"
    post_filter_enabled: bool = True
    strict_mode: bool = True


class ToolsConfig(BaseModel):
    mandatory: list[str] = ["cibrc_safety_check", "imd_weather_check"]
    optional: list[str] = []
    enforcement: dict[str, object] = {"retry_on_missing": True, "max_retries": 2}


class VoiceConfig(BaseModel):
    provider: str = "sarvam"
    default_language: str = "hi"
    supported_languages: list[str] = ["en", "hi", "bn", "od"]


class FirebaseConfig(BaseModel):
    enabled: bool = True
    fcm_enabled: bool = True
    storage_max_upload_mb: int = 5


class GeoConfig(BaseModel):
    location_hierarchy_csv: str = "bolbhav-data/Location hierarchy.csv"
    neighbour_map_csv: str = "bolbhav-data/District Neighbour Map India.csv"
    imd_stations_csv: str = "bolbhav-data/IMD Agromet advisory locations.csv"
    mandis_csv: str = "bolbhav-data/Agmark Mandis and locations.csv"
    crops_csv: str = "bolbhav-data/Agmark crops.csv"
    apmc_map_csv: str = "bolbhav-data/Mandi (APMC) Map.csv"


_YAML_PATH = "config.yaml"


def _load_yaml(path: str) -> dict[str, Any]:
    """Load and normalize a config YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    # Map logging.level → log_level; drop logging section
    if "logging" in data:
        log_cfg = data.pop("logging")
        if "level" in log_cfg:
            data.setdefault("log_level", log_cfg["level"])
    return data


class YamlSettingsSource(PydanticBaseSettingsSource):
    """Lowest-priority source: reads values from config.yaml."""

    def __init__(self, settings_cls: type[BaseSettings], yaml_path: str = "config.yaml") -> None:
        super().__init__(settings_cls)
        self._data = _load_yaml(yaml_path)

    def get_field_value(self, field_name: str, field_info: Any) -> tuple[Any, str, bool]:
        value = self._data.get(field_name)
        return value, field_name, False

    def field_is_complex(self, field: Any) -> bool:
        return True

    def __call__(self) -> dict[str, Any]:
        return {k: v for k, v in self._data.items() if v is not None}


class Settings(BaseSettings):
    """
    Root settings. Priority (high → low): env vars > config.yaml > defaults.

    Env var format: AGRO_<SECTION>__<KEY>, e.g.:
        AGRO_GCP__PROJECT_ID=my-other-project
        AGRO_MODELS__CHAT=gemini-2.0-flash
    """

    gcp: GCPConfig = GCPConfig()
    models: ModelsConfig = ModelsConfig()
    rag: RAGConfig = RAGConfig()
    safety: SafetyConfig = SafetyConfig()
    tools: ToolsConfig = ToolsConfig()
    voice: VoiceConfig = VoiceConfig()
    firebase: FirebaseConfig = FirebaseConfig()
    geo: GeoConfig = GeoConfig()
    log_level: str = "INFO"

    # Secrets (env vars only, never in YAML)
    sarvam_api_key: str = ""
    data_gov_api_key: str = ""
    imd_api_base_url: str = ""

    model_config = {"env_prefix": "AGRO_", "env_nested_delimiter": "__", "env_file": ".env", "env_file_encoding": "utf-8"}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls, _YAML_PATH),
        )

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Settings":
        """Load settings with the given YAML path."""
        global _YAML_PATH
        _YAML_PATH = path
        return cls()


settings = Settings.from_yaml()
