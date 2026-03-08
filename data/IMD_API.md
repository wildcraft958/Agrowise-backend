# IMD Agro WebGIS API Documentation

Based on the analysis of the IMD Agro WebGIS portal (`https://webgis.imd.gov.in/agro/`), here are the key API endpoints used by their dashboard. Currently, these endpoints power the interactive components (location selection, crop stages, alerts).

***Note**: All POST requests require `Content-Type: application/json`. Many of them might also verify the `X-CSRFToken` header, though it may not be strictly enforced if accessed carefully or via session cookies.*

## 1. Location and Region Endpoints
These endpoints fetch hierarchies and coordinates for locations.

### GET `/agro/fetch_options/`
Fetches dropdown options for the location hierarchy.
- **Parameters:**
  - `type`: The level to fetch (`gpcodeState`, `gpcodeDistrict`, `gpcodeBlock`, `gpcodeGP`).
  - `parent_value`: The selected parent value (e.g., state name when fetching districts).
- **Example:** `/agro/fetch_options/?type=gpcodeDistrict&parent_value=Maharashtra`

### GET `/search_lat_lon/`
Fetches coordinates for a specific Gram Panchayat.
- **Parameters:**
  - `type`: `gpcode`
  - `value`: The GP Code string.
- **Example:** `/search_lat_lon/?type=gpcode&value=123456`

### GET `/search_state_district/`
Fetches the bounding box and coordinates for a district.
- **Parameters:** 
  - `state`: State name
  - `district`: District name
- **Example:** `/search_state_district/?state=Gujarat&district=Surat`

## 2. Crop Stage Endpoints
These endpoints fetch phenological stages for crops like Wheat.

### POST `/agro/get_stages_for_state/`
Fetches the crop stages available for a particular state.
- **Payload:**
  ```json
  {
      "state": "Punjab",
      "crop": "wheat"
  }
  ```

### POST `/agro/get_combined_data/`
Fetches combined data tables for a specific crop stage in a state.
- **Payload:**
  ```json
  {
      "state": "Haryana",
      "phenological_stage": "Tillering"
  }
  ```

## 3. Alerts and Disease/Pest Warnings
These endpoints relate weather data to thresholds to issue warnings.

### POST `/agro/get_threshold_data/`
Fetches threshold values for a given crop and stage to check against current weather.
- **Payload:**
  ```json
  {
      "state": "Madhya Pradesh",
      "crop": "wheat",
      "stage": "Heading"
  }
  ```

### POST `/agro/get_warning_messages/`
Fetches warning messages after comparing thresholds with weather.
- **Payload:**
  ```json
  {
      "state": "Madhya Pradesh",
      "crop": "wheat",
      "stage": "Heading",
      "conditions": ["T_Max", "RH_Max"]
  }
  ```

### POST `/agro/get_pest_info/`
Fetches pest information specific to a state, crop, and stage.
- **Payload:**
  ```json
  {
      "state": "Uttar Pradesh",
      "crop": "wheat",
      "stage": "Flowering"
  }
  ```

### POST `/agro/get_wheat_diseases/`
Calculates disease risks based on current weather parameters.
- **Payload:**
  ```json
  {
      "stage": "Anthesis",
      "current_tmax": 32.5,
      "current_tmin": 18.2,
      "current_rh": 65.0,
      "current_rainfall": 0.0
  }
  ```
---

## 4. Mausam Sankalp API Endpoints
The `mausamsankalp.imd.gov.in` portal primarily operates through server-rendered HTML pages where form submissions trigger reloading the whole page (e.g., POST `/cropcurrent`). However, there are a few AJAX-based endpoints to populate dropdowns dynamically.

### POST `/getdist`
Fetches the list of districts for a selected state.
- **Payload (Form Data URL-Encoded):**
  ```
  id=KA&state=KA
  ```
- **Response Example:**
  ```json
  {
      "District": [
          {"id": "Bangalore Urban"},
          {"id": "Bangalore Rural"}
      ],
      "success": "Districts Loaded"
  }
  ```

### POST `/getblock`
Fetches the list of blocks for a selected district.
- **Payload (Form Data URL-Encoded):**
  ```
  id=Bangalore Urban&state=KA
  ```
- **Response Format:** Similar to `/getdist`, returns an array of objects representing blocks under `"District"` key (despite the variable name in JS).

### Server-Rendered Endpoints (Not traditional REST APIs)
The mausam sankalp portal does not return JSON for its primary data (weather parameters threshold table, crop conditions). Instead, submitting the form to `/cropcurrent` returns a fully rendered HTML page containing the tables. 

To use this data in a Web RAG, you would need to:
1. Make a `POST` request to `/cropcurrent` with form data:
   - `State`, `District`, `Block`
   - `Crop` (e.g., `wheat`)
   - `startWeek`
   - `csrf_token`
2. Parse the returned HTML (using a library like BeautifulSoup or Cheerio) to extract the tables containing the TMax, TMin, Rainfall data and thresholds.
3. Convert the parsed HTML tables into a structured JSON string to feed into your LLM context.
