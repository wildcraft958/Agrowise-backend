# IMD Agrometeorology API Documentation

This document centralizes technical details for the two primary IMD portals used by the AgroWise backend:
1. **IMD Agro WebGIS** (`https://webgis.imd.gov.in/agro/`)
2. **Mausam Sankalp** (`https://mausamsankalp.imd.gov.in`)

Implementation can be found in `tools/imd_tool.py`.

---

## 1. IMD Agro WebGIS (JSON APIs)

These endpoints return structured JSON data. Most require a `X-CSRFToken` header, which can be obtained by a preliminary `GET` to the `/agro/` landing page.

### 1.1 Location & Geography
- **`GET /agro/fetch_options/`**
  - Populates hierarchy: `gpcodeState` → `gpcodeDistrict` → `gpcodeBlock` → `gpcodeGP`.
  - **Query Params:** `type`, `parent_value`.
  - **Example:** `?type=gpcodeDistrict&parent_value=Maharashtra`
- **`GET /search_lat_lon/`**
  - **Query Params:** `type=gpcode`, `value=[GP_CODE]`.
- **`GET /search_state_district/`**
  - **Query Params:** `state`, `district`.

### 1.2 Crop Lifecycle & Phenology
- **`POST /agro/get_stages_for_state/`**
  - **Payload:** `{"state": "Punjab", "crop": "wheat"}`
  - **Response:** List of phenological stages (e.g., *Tillering, Booting, Anthesis*).
- **`POST /agro/get_combined_data/`**
  - Fetches weather vs. threshold tables for a specific stage.
  - **Payload:** `{"state": "Haryana", "phenological_stage": "Tillering"}`

### 1.3 Warnings & Risk Analysis
- **`POST /agro/get_threshold_data/`**
  - **Payload:** `{"state": "Punjab", "crop": "wheat", "stage": "Flowering"}`
- **`POST /agro/get_warning_messages/`**
  - Returns agronomic advice for breached thresholds.
  - **Payload:** `{"state": "PB", "crop": "wheat", "stage": "Flowering", "conditions": ["T_Max"]}`
- **`POST /agro/get_pest_info/`**
  - **Payload:** `{"state": "Punjab", "crop": "wheat", "stage": "Flowering"}`
- **`POST /agro/get_wheat_diseases/`**
  - Calculates risk for Yellow Rust, Brown Rust, etc.
  - **Payload:** `{"stage": "Anthesis", "current_tmax": 32, "current_tmin": 15, "current_rh": 65}`

---

## 2. Mausam Sankalp (HTML Scraping)

The Mausam Sankalp portal uses server-rendered HTML. Data is extracted using BeautifulSoup.

### 2.1 Dynamic Dropdowns (JSON)
- **`POST /getdist`**: `id=[STATE_CODE]&state=[STATE_CODE]`
- **`POST /getblock`**: `id=[DISTRICT_NAME]&state=[STATE_CODE]`
- *Note: State codes are 2-letter (e.g., PB, KA).*

### 2.2 Core Data: `/cropcurrent` (HTML)
Requires `csrf_token` in the POST body, extracted from the page source.
- **Location Weather:** Form Data: `State`, `District`, `Block`, `cropsubmit=Submit`.
- **Crop Calendar:** Form Data: `Crop`, `startWeek`, `cropcalsubmit=Submit`.

### 2.3 Parsing Logic & ISM Calendar
Mausam Sankalp uses the **Indian Standard Meteorological (ISM) Calendar** (52 weeks, Week 1 begins Jan 1).
- **Table 1 (Weather):** Contains Rainfall, Tmax, and Tmin. Red cells (inline CSS `color:red`) indicate threshold breaches.
- **Table 2 (Thresholds):** Contains the optimal temperature ranges (e.g., "18-24") per stage.
- **Known Issue:** The portal's HTML often contains unclosed `<td>` tags. The `IMDClient` parser bypasses this by extracting `<b>` tags directly for threshold ranges.

---

## 3. Composite Client Methods

The `IMDClient` in `tools/imd_tool.py` provides high-level methods that combine multiple API calls for easy AI/RAG integration:

| Method | Description |
| :--- | :--- |
| `get_full_crop_advisory()` | Combines WebGIS thresholds + disease risk + pest info + warnings into one JSON. |
| `get_mausam_crop_weather()`| Scrapes historical weather tables and converts them to structured JSON with alerts. |
| `get_full_location_report()`| Merges WebGIS advisory and Mausam Sankalp historical data for a specific coordinate/block. |

---

## 4. Usage Example

```python
from tools.imd_tool import IMDClient

client = IMDClient()
# Get full advisory for a farmer in Punjab
report = client.get_full_crop_advisory(
    state="Punjab", 
    crop="wheat", 
    stage="Tillering", 
    tmax=32, tmin=15, rh=65
)
```
