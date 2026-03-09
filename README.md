# AgroMind Backend

Precision agriculture copilot for Indian smallholder farmers. Gemini-powered agentic backend with mandatory tool enforcement, CIBRC chemical safety filtering, and real-time weather + mandi price integrations.

**GCP Project:** `agrowise-192e3` · **Stack:** Python 3.11+ · FastAPI · LangChain · Gemini via Vertex AI · ChromaDB · Firebase Blaze · Sarvam AI

---

## Architecture

```
User Input (text / voice / image)
        ↓
  Geo-Resolution  →  finds district, IMD station, nearest mandi
        ↓
  Context Enrichment  →  Wikipedia + ICAR RAG + KCC transcripts
        ↓
  Gemini (Vertex AI) + bind_tools(16 tools)
  ├── MANDATORY: cibrc_safety_check, imd_weather_check
  └── OPTIONAL:  kcc_search, soil_moisture, ET calc, mandi_price, diagnosis…
        ↓
  CIBRC Safety Post-filter  →  blocks banned chemicals in response
        ↓
  Firebase  →  persist chat, diagnosis, tool trace · FCM alerts
        ↓
  JSON response  /  Sarvam AI TTS audio
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Managed via `uv` |
| GCP service account JSON | `agrowise-192e3-feea2cfd6558.json` — never committed |
| Vertex AI enabled | Project `agrowise-192e3`, region `us-central1` |
| Firebase Blaze plan | Same service account for Firestore, Storage, FCM |
| Sarvam AI key | ASR + TTS for Indian languages |

---

## Setup

### 1. Install dependencies

```bash
uv pip install -e ".[dev]"
```

### 2. Configure secrets

`GOOGLE_APPLICATION_CREDENTIALS` must point to the service account JSON. This key covers **all** GCP services — Vertex AI, Firebase, Cloud Storage.

```bash
export GOOGLE_APPLICATION_CREDENTIALS=agrowise-192e3-feea2cfd6558.json
```

The `.env` file (gitignored) holds the remaining secrets with the `AGRO_` prefix:

```bash
# .env
AGRO_SARVAM_API_KEY=<your-sarvam-key>
AGRO_DATA_GOV_API_KEY=<your-data.gov.in-key>   # optional — enables live mandi prices
AGRO_IMD_API_BASE_URL=<imd-api-url>             # optional
```

### 3. Verify config loads

```bash
GOOGLE_APPLICATION_CREDENTIALS=agrowise-192e3-feea2cfd6558.json \
  .venv/bin/python -c "from agromind.config import settings; print(settings.models.chat)"
# → gemini-2.5-flash
```

---

## Running the Server

```bash
GOOGLE_APPLICATION_CREDENTIALS=agrowise-192e3-feea2cfd6558.json \
  .venv/bin/uvicorn agromind.main:app --reload --port 8000
```

Or export the credential once and run:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=agrowise-192e3-feea2cfd6558.json
.venv/bin/uvicorn agromind.main:app --reload --port 8000
```

Server starts at `http://localhost:8000`. Swagger UI at `http://localhost:8000/docs`.

---

## API Endpoints

### `GET /health`
```json
{"status": "ok", "version": "0.1.0"}
```

### `POST /agromind/chat`

Main agent endpoint.

```bash
curl -X POST http://localhost:8000/agromind/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What fertilizer should I apply to wheat at tillering stage?",
    "user_id": "farmer_001",
    "language": "en"
  }'
```

Response:
```json
{
  "answer": "Apply 120 kg/ha urea at tillering...",
  "tool_trace": ["cibrc_safety_check", "imd_weather_check"],
  "safety_violation": false,
  "violations": []
}
```

### `POST /diagnosis`

Crop disease detection from a base64-encoded image.

```bash
# Encode an image
IMAGE_B64=$(base64 -w0 leaf.jpg)

curl -X POST http://localhost:8000/diagnosis \
  -H "Content-Type: application/json" \
  -d "{
    \"image_b64\": \"$IMAGE_B64\",
    \"crop\": \"wheat\",
    \"user_id\": \"farmer_001\"
  }"
```

Response:
```json
{
  "disease": "Yellow Rust",
  "confidence": 0.87,
  "severity": "Moderate",
  "affected_area_pct": 35,
  "recommendations": ["Apply propiconazole fungicide", "Remove infected leaves"],
  "additional_notes": "Early stage — intervene within 48 hours"
}
```

---

## Running Standalone Tools

Each tool module has a built-in self-test:

```bash
GOOGLE_APPLICATION_CREDENTIALS=agrowise-192e3-feea2cfd6558.json \
  .venv/bin/python -m tools.cibrc_tool

.venv/bin/python -m tools.imd_tool
.venv/bin/python -m tools.soil_moisture_tool
.venv/bin/python -m tools.evapotranspiration_tool
.venv/bin/python -m tools.kcc_tool
```

---

## Configuration

All non-secret settings are in `config.yaml` (checked into git). Change the model or toggle features without touching code:

```yaml
# Switch LLM globally
models:
  chat: "gemini-2.5-pro"        # upgrade from flash
  vision: "gemini-2.5-flash"

# Disable Firebase for local testing
firebase:
  enabled: false

# Warn instead of block on banned chemicals
safety:
  strict_mode: false
```

Override any value via env: `AGRO_MODELS__CHAT=gemini-2.5-pro uvicorn ...`

---

## Development

```bash
# Tests (all mocked — no live API calls)
.venv/bin/python -m pytest tests/ -x --tb=short

# Coverage
.venv/bin/python -m pytest --cov=agromind --cov-report=term-missing

# Lint + format
.venv/bin/ruff check src/ tests/ tools/
.venv/bin/ruff format src/ tests/ tools/ --check

# Type check
.venv/bin/mypy src/
```

---

## Project Structure

```
├── config.yaml              # Model selection, feature toggles (committed)
├── .env                     # Secrets with AGRO_ prefix (gitignored)
├── src/agromind/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Pydantic settings (YAML + env)
│   ├── agent/               # chain.py · tools.py · mandatory.py · prompt.py
│   ├── api/                 # chat.py · diagnosis.py · health.py
│   ├── diagnosis/           # detector.py · image.py
│   ├── firebase/            # client.py · firestore_ops.py · storage_ops.py · fcm.py
│   ├── geo/                 # resolver · neighbours · imd_stations · mandi_locator
│   ├── ingest/              # pdf_loader · kcc_loader · md_loader
│   ├── market/              # agmarknet.py
│   ├── rag/                 # retriever · wiki_loader · prompt
│   ├── safety/              # validator.py · cibrc.py
│   └── voice/               # asr.py · tts.py
├── tools/                   # Standalone tool modules with self-tests
├── data/                    # cibrc_database.csv · crop_catalogue.json
├── bolbhav-data/            # Geo CSVs (location hierarchy, mandis, IMD stations)
└── tests/                   # 272 unit tests, all mocked
```

---

## Data & Safety

- **CIBRC database** (`data/cibrc_database.csv`): 448 chemicals, 88 currently banned. Loaded at startup, scanned on every response.
- **KCC transcripts**: 221k+ farmer advisory records, bulk-ingestable into ChromaDB.
- **Geo data**: 26 states, 8k+ blocks, 700+ IMD stations, full Agmark mandi coverage.

---

## Environment Variables Reference

```bash
# Required
GOOGLE_APPLICATION_CREDENTIALS=<path-to-service-account.json>

# In .env (auto-loaded, AGRO_ prefix)
AGRO_SARVAM_API_KEY=          # Sarvam AI ASR/TTS
AGRO_DATA_GOV_API_KEY=        # data.gov.in full-access (KCC + mandi)
AGRO_IMD_API_BASE_URL=        # IMD weather API

# Optional config overrides (any config.yaml key)
AGRO_MODELS__CHAT=gemini-2.5-pro
AGRO_MODELS__TEMPERATURE=0.1
AGRO_FIREBASE__ENABLED=false
AGRO_SAFETY__STRICT_MODE=false
```
