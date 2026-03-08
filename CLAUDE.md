# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgroWise is a Python-based agricultural advisory backend built for Indian farmers. It integrates government data sources (IMD weather APIs, CIBRC chemical database) with a neural-symbolic AI engine to deliver crop recommendations via smartphone (PWA) and feature phone (IVR/voice) interfaces.

## Running the Tools

No build step required. Run tools directly as Python modules:

```bash
# Run CIBRC chemical safety tool (with self-tests)
python -m data.cibrc_tool

# Run IMD weather/agrometric tool (with self-tests)
python -m data.imd_tool
```

Both files contain self-test suites that run when executed as `__main__`.

## Architecture

The system follows a **Sense → Analyze → Act** loop:

1. **Sense:** AgroSense IoT spike (ESP32) collects soil moisture/temp/humidity, sends to Firebase
2. **Analyze:** Neural-Symbolic Engine combines:
   - Gemini Flash (computer vision on leaf images + sensor fusion)
   - IMD APIs (real-time weather thresholds, pest/disease risk, crop calendars)
   - CIBRC database (regulatory safety check on any chemical recommendations)
   - ICAR knowledge base (RAG over agronomic reference materials)
3. **Act:** Deliver via PWA dashboard (smartphone) or Kisan-Vani IVR (feature phone via Twilio/Exotel + Sarvam AI TTS)

```
AgroSense (ESP32) → Firebase → Neural-Symbolic Engine → PWA / IVR
```

## Key Files

- **`data/cibrc_tool.py`** — `CIBRCClient` class for chemical safety verification against `cibrc_database.csv` (449 entries). Supports fuzzy matching, batch checks, and status lookups (BANNED/RESTRICTED/REGISTERED). LangChain tool wrappers are present but commented out.
- **`data/imd_tool.py`** — `IMDClient` class integrating two IMD portals: WebGIS JSON APIs (`webgis.imd.gov.in/agro/`) and Mausam Sankalp HTML scraping (`mausamsankalp.imd.gov.in`). Handles CSRF tokens, session management, and location hierarchy (state → district → block → gram panchayat).
- **`data/IMD_API.md`** — Reference documentation for all IMD API endpoints with request/response formats.
- **`architecture.md`** — System architecture with Mermaid diagrams.

## Dependencies

No `requirements.txt` exists yet. Inferred from imports:
- `requests`, `beautifulsoup4`, `lxml` — HTTP and HTML parsing
- Standard library: `csv`, `json`, `logging`, `urllib3`

Install with:
```bash
pip install requests beautifulsoup4 lxml
```

## Integration Notes

- **LangChain:** Both `cibrc_tool.py` and `imd_tool.py` have commented-out LangChain `@tool` wrappers ready to enable.
- **Firebase:** Central orchestrator for IoT data — not in this repo.
- **AI Models:** Gemini Flash (vision/analysis) and Sarvam AI (voice/TTS) are external integrations.
- **SSL:** IMD government servers use self-signed certificates; the IMD client handles this with `verify=False` and suppressed `urllib3` warnings.
- The CIBRC client loads from `data/cibrc_database.csv` relative to the script — keep the CSV co-located with the tool.
