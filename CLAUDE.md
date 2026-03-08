# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgroMind is the **standalone backend** for the AgroWise mobile PWA — a precision agriculture copilot for Indian smallholder farmers. It is an **agentic system** where Gemini Flash decides which tools to invoke based on user input (text, voice-as-text, image, or combinations). Non-agentic **context enrichment layers** (Wikipedia + ICAR/KCC vector RAG + geo-resolution) are injected into the prompt before the LLM call.

**Stack:** Python 3.11+ · FastAPI · LangChain (tool-calling via `bind_tools` on `ChatGoogleGenerativeAI`) · Gemini Flash · ChromaDB · Sarvam AI (voice) · Firebase Blaze (auth, Firestore, Cloud Storage, FCM) · `uv` (package manager)

**Firebase Project:** `agrowise-192e3` (Project ID) · `779023846662` (Project Number) · **Blaze plan** (pay-as-you-go, $0 budget alert set)

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
  │          (routed via IMD station mapping from geo-resolution)│
  └──────────────────────────────────────────────────────────────┘
        ↓
  Gemini Flash (agentic — decides OPTIONAL tools via bind_tools)
  ├── TOOL: kcc_tool          — Live KCC search (fresh/filtered queries)
  ├── TOOL: soil_moisture     — Soil moisture analysis
  ├── TOOL: evapotranspiration — ET-based water requirements
  ├── TOOL: mandi_price_tool  — Live mandi prices from Agmarknet
  └── TOOL: diagnosis_tool    — Image-based disease detection [TODO]
        ↓
  Safety post-filter (CIBRC — validate LLM output has no banned chemicals)
        ↓
  Response → PWA (JSON) / Kisan-Vani IVR (Sarvam AI TTS)
        ↓
  Firebase: persist chat history, diagnosis records, alerts → Firestore
           persist images/audio → Cloud Storage
           push notifications → FCM
```

### Mandatory Tool Enforcement (CIBRC + IMD)

Dual-layer enforcement:
1. **System prompt:** Gemini is instructed to ALWAYS call `cibrc_safety_check` and `imd_weather_check`.
2. **Pipeline validation:** Post-agent validator inspects tool-call trace. If either was NOT called, response is **rejected** and retried with forced calls.

### KCC Dual-Use

1. **Pre-indexed RAG:** 221k+ records bulk-ingested into ChromaDB for zero-latency similarity search.
2. **Live API tool:** Agent can call `kcc_search` / `kcc_get_by_state` for targeted fresh queries.

---

## Firebase Integration (Blaze Plan)

### Why Blaze at $0

Blaze includes all Spark free quotas. For a 50-farmer pilot, estimated daily usage is ~1,060 reads and ~356 writes against limits of 50K reads and 20K writes/day — **under 2% utilization**. Set a $1 budget alert in Google Cloud Console to catch any unexpected usage.

### Free Limits (daily unless noted)

| Service | Free Quota | AgroWise Usage (50-farmer pilot) |
|---|---|---|
| Firestore reads | 50,000/day | ~1,060/day |
| Firestore writes | 20,000/day | ~356/day |
| Firestore storage | 1 GB | ~50 MB (profiles + chat + alerts) |
| Cloud Storage | 5 GB stored, 1 GB/day download | Diagnosis images + voice audio |
| Auth (phone OTP) | 10,000 verifications/month | ~250/month |
| FCM (push) | **Unlimited** | Alerts, advisories |
| Analytics | **Unlimited** | User behavior |
| Hosting | 10 GB transfer/month | PWA static files |

### Cloud Storage Buckets

```
gs://agrowise-192e3.firebasestorage.app/
├── diagnoses/{userId}/{diagnosisId}/
│   └── leaf_image.jpg          # Crop disease photos (max 5 MB each)
├── voice/{userId}/{messageId}/
│   ├── input.wav               # Farmer voice recording (ASR input)
│   └── response.mp3            # AI voice response (TTS output)
└── avatars/{userId}/
    └── profile.jpg             # User profile photos
```

**Storage rules:** Authenticated users can read/write only their own paths. Diagnosis images are write-once (no overwrites). Max file size enforced in security rules.

### Firestore Schema

```
firestore (database: (default))
│
├── users/{userId}
│   ├── name: string
│   ├── phone: string                    # +91XXXXXXXXXX
│   ├── location: string?               # District name
│   ├── avatarUrl: string?              # Cloud Storage URL
│   ├── preferredLanguage: "en" | "hi" | "bn" | "od"
│   ├── createdAt: timestamp
│   └── settings: {
│         isDarkMode: boolean,
│         notificationsEnabled: boolean,
│         voiceEnabled: boolean
│       }
│
├── devices/{deviceId}
│   ├── name: string
│   ├── type: "soil_sensor" | "weather_station" | "irrigation_controller"
│   ├── status: "online" | "offline" | "pairing"
│   ├── batteryLevel: number             # 0-100
│   ├── lastSync: timestamp?
│   ├── fieldId: string?
│   ├── userId: string
│   └── telemetry (subcollection)
│       └── {timestamp}: {
│             soilMoisture: number,      # % VWC
│             temperature: number,       # °C
│             humidity: number           # 0-100
│           }
│
├── fields/{fieldId}
│   ├── name: string
│   ├── area: number?                    # acres
│   ├── soilType: string?               # "Black Cotton" | "Alluvial" | "Red Soil" | "Sandy"
│   ├── location: { latitude, longitude }?
│   ├── crop: {                          # embedded, not subcollection
│   │     id, name, nameHindi?, variety?,
│   │     sowingDate?, expectedHarvestDate?, imageUrl?
│   │   }?
│   ├── devices: string[]               # device IDs
│   └── userId: string
│
├── alerts/{alertId}
│   ├── type: "irrigation" | "disease" | "weather" | "advisory"
│   ├── severity: "critical" | "warning" | "info"
│   ├── title: string
│   ├── message: string
│   ├── timestamp: timestamp
│   ├── isRead: boolean
│   ├── userId: string
│   ├── fieldId: string?
│   └── deviceId: string?
│
├── chats/{userId}/messages/{messageId}
│   ├── role: "user" | "ai"
│   ├── text: string?
│   ├── imageUri: string?               # Cloud Storage URL
│   ├── audioUri: string?               # Cloud Storage URL
│   ├── timestamp: timestamp
│   └── toolTrace: {                     # audit trail
│         cibrcCalled: boolean,
│         imdCalled: boolean,
│         toolsUsed: string[]            # ["kcc_search", "diagnosis_tool", ...]
│       }?                               # only on AI messages
│
├── diagnoses/{diagnosisId}
│   ├── userId: string
│   ├── cropId: string
│   ├── imageUrl: string                 # Cloud Storage URL
│   ├── disease: string?
│   ├── confidence: number               # 0-100
│   ├── recommendations: string[]
│   ├── timestamp: timestamp
│   └── weatherContext: {                # snapshot of weather at diagnosis time
│         temperature, humidity, rainfall?
│       }?
│
├── community/posts/{postId}
│   ├── authorId: string
│   ├── authorName: string
│   ├── authorAvatar: string?
│   ├── content: string
│   ├── image: string?                   # Cloud Storage URL
│   ├── tags: string[]                   # ["Wheat", "Disease", "Success", "Market"]
│   ├── likes: number
│   ├── comments: number
│   ├── likedBy: string[]               # userId array for toggle
│   ├── timestamp: timestamp
│   └── comments (subcollection)
│       └── {commentId}: { authorId, text, timestamp }
│
└── crops/{cropId}                       # static, seeded once
    ├── name: string
    ├── nameHindi: string?
    └── varieties: string[]
```

### Backend Firebase Integration Pattern

The FastAPI backend uses **Firebase Admin SDK** (Python) for:

1. **Token verification:** Middleware validates Firebase ID tokens on protected endpoints. The PWA sends the token in `Authorization: Bearer <token>` header.
2. **Firestore reads/writes:** Backend writes chat history, diagnosis records, and alerts after each agent response. Backend reads user profile + field data for context.
3. **Cloud Storage signed URLs:** Backend generates signed upload URLs for the PWA to upload images/audio directly. Backend reads from storage when processing diagnosis images.
4. **FCM push:** Backend sends push notifications for critical alerts (disease detection, irrigation warnings).

```python
# Backend Firebase init (in agromind/config.py)
import firebase_admin
from firebase_admin import credentials, firestore, storage, messaging

cred = credentials.Certificate("serviceAccountKey.json")  # or GOOGLE_APPLICATION_CREDENTIALS
firebase_admin.initialize_app(cred, {
    "storageBucket": "agrowise-192e3.firebasestorage.app"
})

db = firestore.client()           # Firestore
bucket = storage.bucket()         # Cloud Storage
```

**IMPORTANT:** `serviceAccountKey.json` is NEVER committed to git. Add to `.gitignore`. Use `GOOGLE_APPLICATION_CREDENTIALS` env var in production.

---

## Data Utilization Plan

### Category A — Pre-indexed into ChromaDB (RAG context enrichment)

| Dataset | Location | Chunking Strategy | Metadata Tags |
|---|---|---|---|
| KisanVani Knowledge Base | `data/KisanVani_Knowledge_Base.md` | Section-level | crop, disease, protocol_type |
| Methods Manual Soil Testing | `dataset/` (PDF) | Section-level | test_type, soil_parameter |
| Soil and Water Testing (IARI) | `dataset/` (PDF) | Section-level | test_type |
| ICAR Eng Annual Report 2024-25 | `dataset/` (PDF) | Page-level | topic, year |
| Indian Farming (Nov 2025) | `dataset/` (PDF) | Article-level | crop, region, study_type |
| Integrated Plant Nutrition Mgmt | `dataset/` (PDF) | Section-level | nutrient_type, fertilizer_type |
| KCC transcripts (bulk) | data.gov.in API (paginated) | One doc per record | state, year, month |

**NOT indexed:** `mock_data.md` (testing only), `Hacksagon_Submission.md` (pitch doc).

### Category B — In-memory lookup tables (loaded on startup)

| Dataset | Location | Data Structure | Used By |
|---|---|---|---|
| Location hierarchy | `bolbhav-data/Location hierarchy.csv` | Dict: block → district → state | Geo-resolution |
| District Neighbour Map | `bolbhav-data/District Neighbour Map India.csv` | Adjacency dict: district → [neighbors] | Disease spread, fallback weather |
| IMD Agromet advisory locations | `bolbhav-data/IMD Agromet advisory locations.csv` | Dict: district → IMD station ID | `imd_tool` routing |
| Agmark Mandis + locations | `bolbhav-data/Agmark Mandis and locations.csv` | Dict: district → [mandis with lat/lng] | `mandi_price_tool` |
| Agmark crops | `bolbhav-data/Agmark crops.csv` | Dict: local_name → standard_crop_code | Crop name normalization |
| Mandi (APMC) Map | `bolbhav-data/Mandi (APMC) Map.csv` | Dict: mandi → district → state | Join with location hierarchy |
| CIBRC database | `data/cibrc_database.csv` | Set of banned names + lookup | `cibrc_tool` + safety filter |
| Crop catalogue | `data/crop_catalogue.json` | List: crops with Hindi names | Prompt construction |

### Category C — Live API tools (agent-callable)

| Tool | Mandatory? | Data Source |
|---|---|---|
| `cibrc_tool` | **YES** | `cibrc_database.csv` |
| `imd_tool` | **YES** | IMD APIs via station mapping |
| `kcc_tool` | No | data.gov.in live API |
| `soil_moisture_tool` | No | Sensor data / calculations |
| `evapotranspiration_tool` | No | ET calculations |
| `mandi_price_tool` | No | Agmarknet |
| `diagnosis_tool` | No | Gemini vision |

---

## Existing Code

### `tools/` — Already built, self-contained modules with `__main__` self-tests

| Module | Class/Function | What it does |
|---|---|---|
| `cibrc_tool.py` | `CIBRCClient` | Chemical safety verification (448 chemicals) |
| `imd_tool.py` | `IMDClient` | Weather data from IMD WebGIS + Mausam Sankalp |
| `soil_moisture_tool.py` | — | Soil moisture analysis, irrigation mapping |
| `evapotranspiration_tool.py` | — | ET-based water requirement calculations |
| `kcc_tool.py` | `KCCClient` | KCC farmer query transcripts from data.gov.in |

### Integration notes
- **SSL:** IMD servers use self-signed certs — `IMDClient` handles with `verify=False`.
- **Paths:** Tools expect `data/` relative to project root.
- **CIBRC audit:** Dicofol, Dinocap, Methomyl confirmed BANNED per manual reconciliation.
- **KCC API key:** Default sample key limited to 10 records/call.
- **IMD API:** Reference docs in `data/IMD_API.md`.

---

## TDD Discipline — MANDATORY

Every feature follows **RED → GREEN → REFACTOR**. No exceptions.

1. **RED:** Write a FAILING test. Do NOT write implementation. Run `pytest` — confirm failure.
2. **GREEN:** Write MINIMUM code to pass. Run `pytest` — confirm pass.
3. **REFACTOR:** Clean up. Run `pytest` + `ruff check` + `mypy` — all must pass.
4. **COMMIT GATE:** Only commit when all three pass.

### Rules

- One RED→GREEN→REFACTOR cycle per response.
- Tests drive design. Never implementation-first.
- Mock all external APIs (Gemini, Sarvam, IMD, Wikipedia, KCC, Agmarknet, Firebase) in tests.
- For Firebase: use `unittest.mock` to mock `firebase_admin` calls. Do NOT require a live Firebase connection in tests.
- Test file mirrors source: `src/agromind/geo/resolver.py` → `tests/geo/test_resolver.py`.

---

## Project Structure

```
agromind-backend/
├── CLAUDE.md
├── pyproject.toml
├── .gitignore                   # includes serviceAccountKey.json
├── src/
│   └── agromind/
│       ├── __init__.py
│       ├── main.py              # FastAPI app + Firebase init
│       ├── config.py            # pydantic-settings + Firebase config
│       ├── middleware/          
│       │   ├── __init__.py
│       │   └── auth.py          # Firebase token verification middleware
│       ├── geo/                 # Geo-resolution (bolbhav-data)
│       │   ├── __init__.py
│       │   ├── resolver.py      # Location → district/state/block
│       │   ├── neighbours.py    # District adjacency graph
│       │   ├── imd_stations.py  # District → IMD station ID
│       │   ├── mandi_locator.py # District → nearest mandis
│       │   └── crop_normalizer.py
│       ├── rag/                 # Context enrichment
│       │   ├── __init__.py
│       │   ├── retriever.py     # ChromaDB vector search
│       │   ├── wiki_loader.py   # Wikipedia (multilingual)
│       │   └── prompt.py        # Prompt templates
│       ├── safety/              # CIBRC safety
│       │   ├── __init__.py
│       │   ├── cibrc.py         # Banned chemical set
│       │   └── validator.py     # Post-LLM output validation
│       ├── agent/               # Agent assembly
│       │   ├── __init__.py
│       │   ├── chain.py         # Gemini + bind_tools + prompt
│       │   ├── mandatory.py     # Mandatory tool enforcement
│       │   └── tools.py         # LangChain @tool wrappers
│       ├── diagnosis/
│       │   ├── __init__.py
│       │   ├── image.py         # Preprocessing for Gemini vision
│       │   └── detector.py      # Disease detection tool
│       ├── market/
│       │   ├── __init__.py
│       │   └── agmarknet.py     # Live mandi price fetcher
│       ├── weather/
│       │   ├── __init__.py
│       │   └── imd.py           # IMD client (geo station mapping)
│       ├── voice/
│       │   ├── __init__.py
│       │   ├── asr.py           # Sarvam AI speech-to-text
│       │   └── tts.py           # Sarvam AI text-to-speech
│       ├── firebase/            # Firebase integration layer
│       │   ├── __init__.py
│       │   ├── client.py        # Firebase Admin SDK init + helpers
│       │   ├── firestore_ops.py # CRUD for all collections
│       │   ├── storage_ops.py   # Upload/download/signed URLs
│       │   └── fcm.py           # Push notification sender
│       ├── ingest/
│       │   ├── __init__.py
│       │   ├── pdf_loader.py    # ICAR PDFs → ChromaDB
│       │   ├── kcc_loader.py    # KCC bulk → ChromaDB
│       │   └── md_loader.py     # Markdown → ChromaDB
│       └── api/
│           ├── __init__.py
│           ├── chat.py          # POST /agromind/chat
│           ├── diagnosis.py     # POST /diagnosis
│           └── health.py        # GET /health
├── tools/                       # Existing tools (untouched)
├── data/
├── dataset/
├── bolbhav-data/
└── tests/
    ├── conftest.py              # Firebase mocks, ChromaDB fixtures
    ├── geo/
    ├── rag/
    ├── safety/
    ├── agent/
    ├── market/
    ├── diagnosis/
    ├── weather/
    ├── voice/
    ├── firebase/
    ├── ingest/
    └── api/
```

---

## Implementation Phases

> **Work in phases. Complete each fully. Present summary after each and WAIT for human approval.**

### Phase 1: Project Skeleton + Wrap Existing Tools
**Status:** `TODO`
- [ ] `pyproject.toml`, `src/agromind/` structure, `.gitignore`
- [ ] RED/GREEN/REFACTOR: Wrap all 5 tool modules as LangChain `@tool`s (6 tools total)

### Phase 2: Geo-Resolution Layer (bolbhav-data)
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: `LocationResolver`, `NeighbourGraph`, `IMDStationMapper`, `MandiLocator`, `CropNormalizer`

### Phase 3: Context Enrichment — Wikipedia + ICAR RAG + KCC Bulk
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: Wikipedia multilingual loader with caching
- [ ] RED/GREEN/REFACTOR: PDF + Markdown ingestion → ChromaDB
- [ ] RED/GREEN/REFACTOR: KCC bulk paginated fetch → ChromaDB
- [ ] RED/GREEN/REFACTOR: Unified retriever with metadata filtering

### Phase 4: Mandi Price Tool
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: `AgmarknetClient` + `mandi_price_tool` wrapper

### Phase 5: Agent Assembly — Prompt + Tools + Mandatory Enforcement + Safety
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: System prompt with mandatory tool instructions
- [ ] RED/GREEN/REFACTOR: Context enrichment injection (wiki + ICAR + KCC + geo)
- [ ] RED/GREEN/REFACTOR: Agent creation with `bind_tools` (all 7 tools)
- [ ] RED/GREEN/REFACTOR: Mandatory tool validator (reject if CIBRC/IMD not called, retry)
- [ ] RED/GREEN/REFACTOR: CIBRC safety post-filter on final output

### Phase 6: Firebase Integration Layer
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: Firebase Admin SDK init + config
- [ ] RED/GREEN/REFACTOR: Auth middleware (verify ID tokens)
- [ ] RED/GREEN/REFACTOR: Firestore CRUD — users, chats, diagnoses, alerts
- [ ] RED/GREEN/REFACTOR: Cloud Storage — signed upload URLs, image retrieval
- [ ] RED/GREEN/REFACTOR: FCM — push critical alerts
- [ ] RED/GREEN/REFACTOR: Wire into agent pipeline — persist chat history + diagnosis records + tool traces after each response

### Phase 7: Disease Diagnosis (Image Input)
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: Image preprocessing (resize, EXIF strip)
- [ ] RED/GREEN/REFACTOR: `diagnosis_tool` (Gemini vision)
- [ ] RED/GREEN/REFACTOR: End-to-end with Cloud Storage image retrieval

### Phase 8: Voice Pipeline (Sarvam AI ASR/TTS)
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: ASR client (audio → text)
- [ ] RED/GREEN/REFACTOR: TTS client (text → audio)
- [ ] RED/GREEN/REFACTOR: Voice audio stored in Cloud Storage

### Phase 9: FastAPI Routes + Full Integration
**Status:** `TODO`
- [ ] RED/GREEN/REFACTOR: `POST /agromind/chat` (auth middleware → agent → Firestore persist)
- [ ] RED/GREEN/REFACTOR: `POST /diagnosis` (auth → Cloud Storage image → agent → Firestore)
- [ ] RED/GREEN/REFACTOR: `GET /health`

### Phase 10 (Deferred): Community, Analytics, Advanced Features
- Community posts/comments — Firestore client-side from PWA, no backend API
- Analytics dashboards — PWA reads Firestore directly
- Advanced: Kisan-Vani IVR (Twilio/Exotel integration), offline edge AI (Gemma 3n)

---

## Mobile PWA Integration Points

| PWA Screen | Backend Endpoint | Firebase Direct? |
|---|---|---|
| AgroMind chat | `POST /agromind/chat` | No — goes through backend agent |
| Diagnosis | `POST /diagnosis` | Image upload → Cloud Storage (signed URL from backend) |
| Dashboard weather | `GET /weather?lat=X&lng=Y` | No — backend proxies IMD |
| Health | `GET /health` | No |
| Community | — | **Yes** — PWA reads/writes Firestore directly |
| Profile | — | **Yes** — PWA reads/writes Firestore directly |
| Devices/Fields | — | **Yes** — PWA reads/writes Firestore directly |
| Alerts (read/unread) | — | **Yes** — PWA reads Firestore, backend writes alerts |
| Login (OTP) | — | **Yes** — Firebase Auth client SDK in PWA |

---

## Code Style

- Python 3.11+ with type hints everywhere.
- `ruff` for lint + format (line length 99).
- `mypy` strict mode on `src/`.
- `pydantic v2` for models and settings.
- `httpx` for async HTTP (not `requests`).
- `async def` for all I/O-bound operations.
- Google-style docstrings, brief.
- **No LangGraph. No AgentExecutor.** Use LangChain `bind_tools` + LCEL.
- Firebase Admin SDK for all server-side Firebase operations.

---

## Environment Variables

```bash
GOOGLE_API_KEY=                    # Gemini Flash
GOOGLE_APPLICATION_CREDENTIALS=    # Path to Firebase service account JSON
SARVAM_API_KEY=                    # Sarvam AI ASR/TTS
IMD_API_BASE_URL=                  # IMD weather API base
DATA_GOV_API_KEY=                  # data.gov.in (KCC full access)
CHROMA_PERSIST_DIR=./chroma_db
FIREBASE_STORAGE_BUCKET=agrowise-192e3.firebasestorage.app
LOG_LEVEL=INFO
```

---

## Git Conventions

- Messages: `feat(firebase): add Firestore chat persistence`
- Prefixes: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`
- Each TDD cycle → one commit.
- Branch: `phase-N/description` (e.g., `phase-6/firebase-integration`)
- **NEVER commit:** `serviceAccountKey.json`, `.env`, `chroma_db/`

---

## Cost Control (Blaze Plan)

- **Budget alert:** Set at $1/month in Google Cloud Console → Billing → Budgets.
- **Firestore security rules:** Enforce per-user read/write paths to prevent abuse.
- **Cloud Storage rules:** Max 5 MB per upload, authenticated users only, write to own path only.
- **Rate limiting:** FastAPI middleware limits requests per user (e.g., 30 chat messages/hour).
- **Monitor:** Check Firebase Console → Usage & Billing weekly during pilot.