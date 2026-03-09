# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgroMind is the **standalone backend** for the AgroWise mobile PWA — a precision agriculture copilot for Indian smallholder farmers. It is an **agentic system** where Gemini (via Vertex AI) decides which tools to invoke based on user input (text, voice-as-text, image, or combinations). Non-agentic **context enrichment layers** (Wikipedia + ICAR/KCC vector RAG + geo-resolution) are injected into the prompt before the LLM call.

**Stack:** Python 3.11+ · FastAPI · LangChain + `langchain-google-vertexai` · Gemini via Vertex AI · ChromaDB · Sarvam AI (voice) · Firebase Blaze (Firestore, Cloud Storage, Auth, FCM) · `uv` (package manager)

**GCP Project:** `agrowise-192e3` · Project Number `779023846662` · **Blaze plan** ($300 free credits)
**Service Account:** `agrowise-vertex-sa` — single SA for Vertex AI + Firebase Admin SDK
**Auth model:** `GOOGLE_APPLICATION_CREDENTIALS` → all GCP services (Vertex AI, Firebase, Cloud Storage) authenticate via the same service account JSON. No separate API keys needed for Google services.

---

## Commands

```bash
# Install
uv pip install -e ".[dev]"

# Run existing tools (self-test)
python -m tools.cibrc_tool
python -m tools.imd_tool
python -m tools.soil_moisture_tool
python -m tools.evapotranspiration_tool
python -m tools.kcc_tool

# Testing (TDD)
pytest                                          # All tests
pytest tests/ -x --tb=short                     # Stop on first failure
pytest --cov=agromind --cov-report=term-missing  # Coverage

# Lint & type check
ruff check src/ tests/ tools/
ruff format src/ tests/ tools/ --check
mypy src/

# Dev server
uvicorn agromind.main:app --reload --port 8000
```

---

## Configuration System

All configuration lives in `src/agromind/config.py` using **pydantic-settings**. Values come from a `config.yaml` (defaults + model selection + feature toggles) overlaid with environment variables (secrets + overrides).

### `config.yaml` — Checked into git (no secrets)

```yaml
# config.yaml — AgroWise Backend Configuration
# Toggle features and select models without code changes.

gcp:
  project_id: "agrowise-192e3"
  location: "us-central1"
  storage_bucket: "agrowise-192e3.firebasestorage.app"

models:
  # Change model here to switch globally. No code changes needed.
  chat: "gemini-2.5-flash"          # Main agent model (tool-calling)
  vision: "gemini-2.5-flash"        # Diagnosis image analysis
  embedding: "text-embedding-005"   # ChromaDB embeddings (Vertex AI)
  temperature: 0.2                  # Lower = more deterministic for agriculture advice
  max_output_tokens: 2048

rag:
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5                          # Number of context chunks to retrieve
  chroma_persist_dir: "./chroma_db"
  collections:
    icar: "icar_knowledge"
    kcc: "kcc_transcripts"

safety:
  cibrc_csv_path: "data/cibrc_database.csv"
  post_filter_enabled: true         # Scan LLM output for banned chemicals
  strict_mode: true                 # Reject response (not just warn) if banned chemical found

tools:
  mandatory:
    - "cibrc_safety_check"
    - "imd_weather_check"
  optional:
    - "kcc_search"
    - "kcc_get_by_state"
    - "soil_moisture_analysis"
    - "evapotranspiration_calc"
    - "mandi_price_lookup"
    - "diagnosis_tool"
  enforcement:
    retry_on_missing: true          # Retry if mandatory tool not called
    max_retries: 2

voice:
  provider: "sarvam"               # Switch to "bhashini" if needed
  default_language: "hi"
  supported_languages: ["en", "hi", "bn", "od"]

firebase:
  enabled: true                    # Set false to run backend without Firebase (testing)
  fcm_enabled: true
  storage_max_upload_mb: 5

geo:
  location_hierarchy_csv: "bolbhav-data/Location hierarchy.csv"
  neighbour_map_csv: "bolbhav-data/District Neighbour Map India.csv"
  imd_stations_csv: "bolbhav-data/IMD Agromet advisory locations.csv"
  mandis_csv: "bolbhav-data/Agmark Mandis and locations.csv"
  crops_csv: "bolbhav-data/Agmark crops.csv"
  apmc_map_csv: "bolbhav-data/Mandi (APMC) Map.csv"

logging:
  level: "INFO"
```

### `src/agromind/config.py` — Pydantic settings loader

```python
"""
Centralized configuration for AgroMind backend.

Loads from config.yaml (defaults, model selection, feature toggles)
with environment variable overrides for secrets.

Usage:
    from agromind.config import settings
    llm = ChatVertexAI(
        model_name=settings.models.chat,
        project=settings.gcp.project_id,
        location=settings.gcp.location,
        temperature=settings.models.temperature,
    )
"""

import yaml
from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings


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


class Settings(BaseSettings):
    """
    Root settings. Env vars override YAML values.

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

    model_config = {"env_prefix": "AGRO_", "env_nested_delimiter": "__"}

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Settings":
        """Load from YAML file, then overlay env vars."""
        config_path = Path(path)
        if config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f) or {}
            return cls(**yaml_data)
        return cls()


settings = Settings.from_yaml()
```

### How it works

1. **Model switching:** Change `models.chat` in `config.yaml` from `gemini-2.5-flash` to `gemini-2.5-pro` — no code changes, just restart.
2. **Feature toggles:** Set `firebase.enabled: false` to run the agent pipeline without Firebase (useful for local testing). Set `safety.strict_mode: false` to warn instead of reject on banned chemicals.
3. **Secrets via env:** `GOOGLE_APPLICATION_CREDENTIALS`, `AGRO_SARVAM_API_KEY`, `AGRO_DATA_GOV_API_KEY` — never in YAML or git.
4. **Env overrides:** Any YAML value can be overridden: `AGRO_MODELS__CHAT=gemini-2.0-flash uvicorn agromind.main:app`

---

## Architecture: Sense → Analyze → Act

```
Inputs (text / voice-as-text / image / IoT telemetry)
        ↓
  ┌──────────────────────────────────────────────────────────────┐
  │  GEO-RESOLUTION (deterministic, pre-LLM)                   │
  │  ├── Location hierarchy lookup → State/District/Block       │
  │  ├── District neighbour graph → adjacent districts          │
  │  ├── IMD station mapping → correct IMD station ID           │
  │  └── Nearest mandi lookup → Agmark mandis for the area     │
  └──────────────────────────────────────────────────────────────┘
        ↓
  ┌──────────────────────────────────────────────────────────────┐
  │  CONTEXT ENRICHMENT (deterministic RAG, pre-LLM)            │
  │  ├── Wikipedia fetch (multilingual, lang param)             │
  │  ├── ICAR knowledge base RAG (ChromaDB similarity)          │
  │  │   └── Soil manuals, plant nutrition, ICAR reports,       │
  │  │       Indian Farming articles, KisanVani protocols       │
  │  └── KCC pre-indexed transcripts (ChromaDB similarity)      │
  └──────────────────────────────────────────────────────────────┘
        ↓
  ┌──────────────────────────────────────────────────────────────┐
  │  MANDATORY TOOL CALLS (always invoked, pipeline-validated)  │
  │  ├── TOOL: cibrc_tool  — Chemical safety lookup             │
  │  └── TOOL: imd_tool    — Real-time weather/advisories       │
  └──────────────────────────────────────────────────────────────┘
        ↓
  Gemini via Vertex AI (agentic — decides OPTIONAL tools via bind_tools)
  ├── TOOL: kcc_tool          — Live KCC search
  ├── TOOL: soil_moisture     — Soil moisture analysis
  ├── TOOL: evapotranspiration — ET-based water requirements
  ├── TOOL: mandi_price_tool  — Live mandi prices from Agmarknet
  └── TOOL: diagnosis_tool    — Image-based disease detection [TODO]
        ↓
  Safety post-filter (CIBRC — validate LLM output has no banned chemicals)
        ↓
  Firebase: persist chat + diagnosis + tool trace → Firestore
            persist images/audio → Cloud Storage
            push critical alerts → FCM
        ↓
  Response → PWA (JSON) / Kisan-Vani IVR (Sarvam AI TTS)
```

### Vertex AI Integration Pattern

All LLM calls go through Vertex AI, authenticated via service account:

```python
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from agromind.config import settings

# Agent LLM (tool-calling)
llm = ChatVertexAI(
    model_name=settings.models.chat,
    project=settings.gcp.project_id,
    location=settings.gcp.location,
    temperature=settings.models.temperature,
    max_output_tokens=settings.models.max_output_tokens,
)

# Embeddings for ChromaDB (ICAR + KCC ingestion + retrieval)
embeddings = VertexAIEmbeddings(
    model_name=settings.models.embedding,
    project=settings.gcp.project_id,
    location=settings.gcp.location,
)

# Tool binding
agent = llm.bind_tools([cibrc_tool, imd_tool, kcc_search, ...])
```

**No API keys in code.** `GOOGLE_APPLICATION_CREDENTIALS` env var points to the service account JSON. LangChain's Vertex AI integration, Firebase Admin SDK, and Cloud Storage all pick it up automatically.

**Billing:** All Vertex AI calls bill to project `agrowise-192e3` against the $300 free GCP credits.

### Mandatory Tool Enforcement (CIBRC + IMD)

Dual-layer enforcement:
1. **System prompt:** Gemini is instructed to ALWAYS call mandatory tools (list from `config.yaml`).
2. **Pipeline validation:** Post-agent validator inspects tool-call trace. If any mandatory tool not called, response is rejected and retried (configurable via `tools.enforcement` in config).

### KCC Dual-Use

1. **Pre-indexed RAG:** 221k+ records bulk-ingested into ChromaDB (Vertex AI embeddings).
2. **Live API tool:** Agent can call `kcc_search` / `kcc_get_by_state` for targeted fresh queries.

---

## Firebase Integration (Blaze Plan, $0 target)

### Architecture

```
┌─────────────────────────────────────────────────┐
│  FIREBASE (same service account as Vertex AI)   │
│                                                 │
│  Auth          → OTP phone login (+91)          │
│  Firestore     → Users, chats, diagnoses,       │
│                  alerts, community, fields,      │
│                  devices + telemetry, crops      │
│  Cloud Storage → Diagnosis images, voice audio,  │
│                  user avatars                    │
│  FCM           → Push notifications             │
│  Analytics     → User behavior (unlimited free) │
└─────────────────────────────────────────────────┘
```

### Cloud Storage Buckets

```
gs://agrowise-192e3.firebasestorage.app/
├── diagnoses/{userId}/{diagnosisId}/leaf_image.jpg
├── voice/{userId}/{messageId}/input.wav
├── voice/{userId}/{messageId}/response.mp3
└── avatars/{userId}/profile.jpg
```

### Firestore Schema

```
firestore (database: (default))
│
├── users/{userId}
│   ├── name, phone (+91XXXXXXXXXX), location?, avatarUrl?
│   ├── preferredLanguage: "en"|"hi"|"bn"|"od"
│   ├── createdAt: timestamp
│   └── settings: { isDarkMode, notificationsEnabled, voiceEnabled }
│
├── devices/{deviceId}
│   ├── name, type, status, batteryLevel, lastSync?, fieldId?, userId
│   └── telemetry/{timestamp}: { soilMoisture, temperature, humidity }
│
├── fields/{fieldId}
│   ├── name, area?, soilType?, location?, crop? (embedded), devices[], userId
│
├── alerts/{alertId}
│   ├── type, severity, title, message, timestamp, isRead, userId, fieldId?, deviceId?
│
├── chats/{userId}/messages/{messageId}
│   ├── role: "user"|"ai", text?, imageUri?, audioUri?, timestamp
│   └── toolTrace?: { cibrcCalled, imdCalled, toolsUsed[] }
│
├── diagnoses/{diagnosisId}
│   ├── userId, cropId, imageUrl, disease?, confidence, recommendations[]
│   ├── timestamp, weatherContext?
│
├── community/posts/{postId}
│   ├── authorId, authorName, content, image?, tags[], likes, comments
│   ├── likedBy[], timestamp
│   └── comments/{commentId}: { authorId, text, timestamp }
│
└── crops/{cropId}  — static, seeded once
    ├── name, nameHindi?, varieties[]
```

### Backend Firebase Init

```python
# Uses same GOOGLE_APPLICATION_CREDENTIALS as Vertex AI
import firebase_admin
from firebase_admin import credentials, firestore, storage, messaging
from agromind.config import settings

cred = credentials.ApplicationDefault()  # picks up service account automatically
firebase_admin.initialize_app(cred, {
    "storageBucket": settings.gcp.storage_bucket
})

db = firestore.client()
bucket = storage.bucket()
```

### Cost Control

- $300 GCP free credits cover everything (Vertex AI + Firebase).
- Budget alert at $5/month in Cloud Console.
- Firestore security rules enforce per-user paths.
- Cloud Storage max upload: 5 MB (configurable in `config.yaml`).
- FastAPI rate limiting: 30 chat messages/user/hour.

---

## Data Utilization Plan

### Category A — Pre-indexed into ChromaDB (Vertex AI Embeddings)

| Dataset | Chunking | Metadata |
|---|---|---|
| KisanVani Knowledge Base | Section-level | crop, disease, protocol_type |
| Soil Testing Manual (GOI) | Section-level | test_type, soil_parameter |
| Soil & Water Testing (IARI) | Section-level | test_type |
| ICAR Annual Report 2024-25 | Page-level | topic, year |
| Indian Farming (Nov 2025) | Article-level | crop, region |
| Plant Nutrition Management | Section-level | nutrient_type |
| KCC transcripts (bulk 221k+) | One doc/record | state, year, month |

### Category B — In-memory lookup tables (startup)

| Dataset | Used By |
|---|---|
| `Location hierarchy.csv` | Geo-resolution |
| `District Neighbour Map India.csv` | Disease spread, fallback weather |
| `IMD Agromet advisory locations.csv` | `imd_tool` station routing |
| `Agmark Mandis and locations.csv` | `mandi_price_tool` |
| `Agmark crops.csv` | Crop name normalization |
| `Mandi (APMC) Map.csv` | Mandi → district join |
| `cibrc_database.csv` | Safety filter |
| `crop_catalogue.json` | Prompt construction |

### Category C — Live API tools

| Tool | Mandatory? | Source |
|---|---|---|
| `cibrc_tool` | **YES** | CIBRC CSV |
| `imd_tool` | **YES** | IMD APIs |
| `kcc_tool` | No | data.gov.in |
| `soil_moisture_tool` | No | Calculations |
| `evapotranspiration_tool` | No | ET calcs |
| `mandi_price_tool` | No | Agmarknet |
| `diagnosis_tool` | No | Gemini vision (Vertex AI) |

---

## Existing Code

### `tools/` — Self-contained modules with `__main__` self-tests

| Module | Class | Purpose |
|---|---|---|
| `cibrc_tool.py` | `CIBRCClient` | Chemical safety (448 chemicals) |
| `imd_tool.py` | `IMDClient` | IMD WebGIS + Mausam Sankalp |
| `soil_moisture_tool.py` | — | Soil moisture analysis |
| `evapotranspiration_tool.py` | — | ET water requirements |
| `kcc_tool.py` | `KCCClient` | KCC farmer transcripts |

### Notes
- IMD: `verify=False` (self-signed certs). KCC: sample key = 10 records/call.
- CIBRC: Dicofol, Dinocap, Methomyl confirmed BANNED (March 2026 audit).

---

## TDD Discipline — MANDATORY

**RED → GREEN → REFACTOR.** One cycle per response.

1. **RED:** Failing test. No implementation. `pytest` confirms failure.
2. **GREEN:** Minimum code to pass. `pytest` confirms pass.
3. **REFACTOR:** Clean up. `pytest` + `ruff check` + `mypy` all pass.
4. **COMMIT GATE:** All three green before commit.

**Mocking:** Mock Vertex AI (`ChatVertexAI`, `VertexAIEmbeddings`), Firebase (`firebase_admin`), all external APIs. No live connections in tests.

---

## Project Structure

```
agromind-backend/
├── CLAUDE.md
├── config.yaml                  # Model selection, feature toggles (checked in)
├── pyproject.toml
├── .gitignore                   # SA JSON, .env, chroma_db/
├── src/
│   └── agromind/
│       ├── __init__.py
│       ├── main.py              # FastAPI app + Firebase init
│       ├── config.py            # Pydantic settings (YAML + env)
│       ├── middleware/
│       │   └── auth.py          # Firebase token verification
│       ├── geo/                 # bolbhav-data lookups
│       │   ├── resolver.py, neighbours.py, imd_stations.py
│       │   ├── mandi_locator.py, crop_normalizer.py
│       ├── rag/
│       │   ├── retriever.py     # ChromaDB (Vertex AI embeddings)
│       │   ├── wiki_loader.py   # Wikipedia multilingual
│       │   └── prompt.py        # Prompt templates
│       ├── safety/
│       │   ├── cibrc.py         # Banned chemical set
│       │   └── validator.py     # Post-LLM output scan
│       ├── agent/
│       │   ├── chain.py         # ChatVertexAI + bind_tools + prompt
│       │   ├── mandatory.py     # Mandatory tool enforcement
│       │   └── tools.py         # @tool wrappers
│       ├── diagnosis/
│       │   ├── image.py         # Preprocessing
│       │   └── detector.py      # Gemini vision via Vertex AI
│       ├── market/
│       │   └── agmarknet.py     # Live mandi prices
│       ├── weather/
│       │   └── imd.py           # IMD client
│       ├── voice/
│       │   ├── asr.py           # Sarvam AI STT
│       │   └── tts.py           # Sarvam AI TTS
│       ├── firebase/
│       │   ├── client.py        # Admin SDK init (ApplicationDefault creds)
│       │   ├── firestore_ops.py # Collection CRUD
│       │   ├── storage_ops.py   # Signed URLs, upload/download
│       │   └── fcm.py           # Push notifications
│       ├── ingest/
│       │   ├── pdf_loader.py    # ICAR PDFs → ChromaDB
│       │   ├── kcc_loader.py    # KCC bulk → ChromaDB
│       │   └── md_loader.py     # Markdown → ChromaDB
│       └── api/
│           ├── chat.py          # POST /agromind/chat
│           ├── diagnosis.py     # POST /diagnosis
│           └── health.py        # GET /health
├── tools/                       # Existing (untouched)
├── data/, dataset/, bolbhav-data/
└── tests/
    ├── conftest.py              # Vertex AI mocks, Firebase mocks, ChromaDB fixtures
    └── geo/, rag/, safety/, agent/, market/, diagnosis/,
        weather/, voice/, firebase/, ingest/, api/
```

---

## Implementation Phases

> **Complete each phase fully. Present summary and WAIT for approval.**

### Phase 1: Project Skeleton + Config + Wrap Tools
**Status:** `COMPLETE` ✓
- [x] `pyproject.toml` (all deps including `beautifulsoup4`, `lxml` added)
- [x] `config.yaml` + `src/agromind/config.py` (pydantic-settings with YAML source, env override)
- [x] RED/GREEN/REFACTOR: Config loading — YAML defaults, env overrides, model switching (5 tests)
- [x] RED/GREEN/REFACTOR: All 5 tool modules wrapped as LangChain `@tool`s — **15 tools total** (2 mandatory + 13 optional) with full feature coverage (56 tests)
- [x] RED/GREEN/REFACTOR: Verify `ChatVertexAI` + `VertexAIEmbeddings` initialize with config values (mocked)

**Tools in `src/agromind/agent/tools.py`:**
| Tool | Type | Wraps |
|---|---|---|
| `cibrc_safety_check` | MANDATORY | `CIBRCClient.check_chemical_safety` |
| `imd_weather_check` | MANDATORY | `IMDClient.get_full_crop_advisory` |
| `cibrc_check_batch` | optional | `CIBRCClient.check_batch` |
| `cibrc_list_banned` | optional | `CIBRCClient.list_banned` |
| `cibrc_list_restricted` | optional | `CIBRCClient.list_restricted` |
| `cibrc_list_proposed_ban` | optional | `CIBRCClient.list_proposed_ban` |
| `kcc_search` | optional | `KCCClient.search_queries` |
| `kcc_get_by_state` | optional | `KCCClient.get_by_state` |
| `soil_moisture_analysis` | optional | `SoilMoistureClient.get_by_district/state` |
| `evapotranspiration_calc` | optional | `EvapotranspirationClient.get_by_district/state` |
| `imd_crop_stages` | optional | `IMDClient.get_crop_stages` |
| `imd_mausam_weather` | optional | `IMDClient.get_mausam_crop_weather` |
| `imd_crop_calendar` | optional | `IMDClient.get_mausam_crop_calendar` |
| `imd_wheat_disease_risk` | optional | `IMDClient.get_wheat_disease_risk` |
| `imd_pest_info` | optional | `IMDClient.get_pest_info` |

**Notes:**
- Old `langchain.tools.Tool` commented blocks removed from all `tools/` files (clean)
- `YamlSettingsSource` custom pydantic-settings source: priority = env vars > YAML > defaults
- `beautifulsoup4` + `lxml` added to `pyproject.toml` (required by `imd_tool.py`)

### Phase 2: Geo-Resolution Layer
**Status:** `TODO`
- [ ] Inspect actual CSV headers before writing any loader (`head -3` each file)
- [ ] RED/GREEN/REFACTOR: `LocationResolver` — `Location hierarchy.csv`
- [ ] RED/GREEN/REFACTOR: `NeighbourGraph` — `District Neighbour Map India.csv`
- [ ] RED/GREEN/REFACTOR: `IMDStationMapper` — `IMD Agromet advisory locations.csv`
- [ ] RED/GREEN/REFACTOR: `MandiLocator` — `Agmark Mandis and locations.csv` + `Mandi (APMC) Map.csv`
- [ ] RED/GREEN/REFACTOR: `CropNormalizer` — `Agmark crops.csv`

### Phase 3: Context Enrichment — Wikipedia + ICAR RAG + KCC Bulk
**Status:** `TODO`
- [ ] Check each PDF for extractable text before ingesting (some may need OCR)
- [ ] RED/GREEN/REFACTOR: Wikipedia multilingual loader
- [ ] RED/GREEN/REFACTOR: PDF + MD ingestion → ChromaDB (Vertex AI embeddings via config)
- [ ] RED/GREEN/REFACTOR: KCC bulk paginated → ChromaDB
- [ ] RED/GREEN/REFACTOR: Unified retriever with metadata filtering

### Phase 4: Mandi Price Tool
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: `AgmarknetClient` + `mandi_price_tool`

### Phase 5: Agent Assembly
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: System prompt with mandatory tool instructions
- [ ] RED/GREEN/REFACTOR: Context injection (wiki + ICAR + KCC + geo)
- [ ] RED/GREEN/REFACTOR: `ChatVertexAI.bind_tools()` with all 15 tools
- [ ] RED/GREEN/REFACTOR: Mandatory tool validator + retry
- [ ] RED/GREEN/REFACTOR: CIBRC safety post-filter

### Phase 6: Firebase Integration
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: Admin SDK init (ApplicationDefault, toggled via config)
- [ ] RED/GREEN/REFACTOR: Auth middleware
- [ ] RED/GREEN/REFACTOR: Firestore CRUD (users, chats, diagnoses, alerts)
- [ ] RED/GREEN/REFACTOR: Cloud Storage (signed URLs, image retrieval)
- [ ] RED/GREEN/REFACTOR: FCM push
- [ ] RED/GREEN/REFACTOR: Wire into agent — persist chat + diagnosis + tool trace

### Phase 7: Disease Diagnosis
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: Image preprocessing
- [ ] RED/GREEN/REFACTOR: `diagnosis_tool` (Gemini vision via Vertex AI)
- [ ] RED/GREEN/REFACTOR: End-to-end with Cloud Storage

### Phase 8: Voice Pipeline (Sarvam AI)
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: ASR + TTS clients (provider configurable)
- [ ] RED/GREEN/REFACTOR: Voice audio in Cloud Storage

### Phase 9: FastAPI Routes
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: `POST /agromind/chat`, `POST /diagnosis`, `GET /health`

### Phase 10 (Deferred): Community, IVR, Edge AI
- Community — Firestore client-side from PWA
- Kisan-Vani IVR — Twilio/Exotel
- Offline edge AI — Gemma 3n

---

## Mobile PWA Integration

| PWA Screen | Backend? | Firebase Direct? |
|---|---|---|
| AgroMind chat | `POST /agromind/chat` | — |
| Diagnosis | `POST /diagnosis` | Image → Cloud Storage (signed URL) |
| Weather | `GET /weather` | — |
| Community | — | Firestore direct |
| Profile | — | Firestore direct |
| Devices/Fields | — | Firestore direct |
| Alerts | — | Firestore (backend writes, PWA reads) |
| Login | — | Firebase Auth client SDK |

---

## Code Style

- Python 3.11+, type hints everywhere, `ruff` (line 99), `mypy` strict on `src/`.
- `pydantic v2`, `httpx` (not `requests`), `async def` for I/O.
- Google-style docstrings. **No LangGraph. No AgentExecutor.** `bind_tools` + LCEL.
- All GCP services via `GOOGLE_APPLICATION_CREDENTIALS`. No inline API keys.

---

## Environment Variables

```bash
# GCP (single auth for everything)
GOOGLE_APPLICATION_CREDENTIALS=agrowise-192e3-feea2cfd6558.json

# Non-GCP secrets
AGRO_SARVAM_API_KEY=             # Sarvam AI ASR/TTS
AGRO_DATA_GOV_API_KEY=           # data.gov.in (KCC full access)
AGRO_IMD_API_BASE_URL=           # IMD weather API base

# Optional overrides (anything in config.yaml)
# AGRO_MODELS__CHAT=gemini-2.5-pro
# AGRO_MODELS__TEMPERATURE=0.5
# AGRO_FIREBASE__ENABLED=false
```

---

## Git Conventions

- Messages: `feat(config): add model switching via config.yaml`
- Prefixes: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`
- Each TDD cycle → one commit.
- Branch: `phase-N/description`
- **NEVER commit:** `*.json` (service account), `.env`, `chroma_db/`, `__pycache__/`