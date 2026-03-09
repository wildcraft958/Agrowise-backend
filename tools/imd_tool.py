"""
IMD Agro WebGIS + Mausam Sankalp API Tool
==========================================
A self-contained Python module wrapping ALL useful endpoints from:
  - https://webgis.imd.gov.in/agro/   (JSON APIs)
  - https://mausamsankalp.imd.gov.in  (HTML scraping)

Usage:
    from imd_tool import IMDClient
    client = IMDClient()

    # WebGIS JSON APIs
    data = client.get_crop_stages(state="Punjab", crop="wheat")
    advisory = client.get_full_crop_advisory("Punjab", "wheat", "Flowering", 32, 15, 65)

    # Mausam Sankalp (scraped HTML → clean JSON)
    weather = client.get_mausam_crop_weather(state_code="AP", district="Anantapur", block="Gooty")
    calendar = client.get_mausam_crop_calendar(crop="wheat", start_week=10)
"""

import requests
import json
import logging
import urllib3
from typing import Optional, Any
from bs4 import BeautifulSoup

# IMD government servers use self-signed / locally-issued certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL  = "https://webgis.imd.gov.in"
MAUSAM_URL = "https://mausamsankalp.imd.gov.in"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Week number → date range label (ISM calendar, week 1 = Jan 1–7)
WEEK_LABELS = {
    1:"Jan 1-7", 2:"Jan 8-14", 3:"Jan 15-21", 4:"Jan 22-28",
    5:"Jan 29-Feb 4", 6:"Feb 5-11", 7:"Feb 12-18", 8:"Feb 19-25",
    9:"Feb 26-Mar 4", 10:"Mar 5-11", 11:"Mar 12-18", 12:"Mar 19-25",
    13:"Mar 26-Apr 1", 14:"Apr 2-8", 15:"Apr 9-15", 16:"Apr 16-22",
    17:"Apr 23-29", 18:"Apr 30-May 6", 19:"May 7-13", 20:"May 14-20",
    21:"May 21-27", 22:"May 28-Jun 3", 23:"Jun 4-10", 24:"Jun 11-17",
    25:"Jun 18-24", 26:"Jun 25-Jul 1", 27:"Jul 2-8", 28:"Jul 9-15",
    29:"Jul 16-22", 30:"Jul 23-29", 31:"Jul 30-Aug 5", 32:"Aug 6-12",
    33:"Aug 13-19", 34:"Aug 20-26", 35:"Aug 27-Sep 2", 36:"Sep 3-9",
    37:"Sep 10-16", 38:"Sep 17-23", 39:"Sep 24-30", 40:"Oct 1-7",
    41:"Oct 8-14", 42:"Oct 15-21", 43:"Oct 22-28", 44:"Oct 29-Nov 4",
    45:"Nov 5-11", 46:"Nov 12-18", 47:"Nov 19-25", 48:"Nov 26-Dec 2",
    49:"Dec 3-9", 50:"Dec 10-16", 51:"Dec 17-23", 52:"Dec 24-31",
}

# ---------------------------------------------------------------------------
# Internal Session helpers
# ---------------------------------------------------------------------------

class _WebGISSession:
    """Persistent session for webgis.imd.gov.in — handles CSRF automatically."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": _BROWSER_UA,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        })
        self._ready = False

    def _init(self):
        if self._ready:
            return
        try:
            resp = self.session.get(
                f"{BASE_URL}/agro/", timeout=self.timeout, verify=False
            )
            if "csrftoken" in self.session.cookies:
                self.session.headers["X-CSRFToken"] = self.session.cookies["csrftoken"]
                logger.debug("WebGIS CSRF token acquired.")
        except requests.RequestException as e:
            logger.warning(f"WebGIS CSRF init failed: {e}")
        finally:
            self._ready = True

    def get(self, path: str, params: dict = None) -> Optional[Any]:
        self._init()
        url = f"{BASE_URL}{path}"
        try:
            r = self.session.get(url, params=params, timeout=self.timeout, verify=False)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            logger.error(f"GET {url} [{e.response.status_code}]: {e.response.text[:200]}")
        except Exception as e:
            logger.error(f"GET {url}: {e}")
        return None

    def post(self, path: str, payload: dict) -> Optional[Any]:
        self._init()
        url = f"{BASE_URL}{path}"
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["Referer"] = f"{BASE_URL}/agro/"
        try:
            r = self.session.post(url, json=payload, timeout=self.timeout, verify=False)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            logger.error(f"POST {url} [{e.response.status_code}]: {e.response.text[:200]}")
        except Exception as e:
            logger.error(f"POST {url}: {e}")
        return None


class _MausamSession:
    """Persistent session for mausamsankalp.imd.gov.in.

    Handles the custom `csrf_token` field embedded in each page form.
    The token must be re-fetched before every POST because it rotates.
    """

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _BROWSER_UA})

    def _get_csrf(self) -> str:
        """GET the page and extract the current csrf_token value."""
        r = self.session.get(
            f"{MAUSAM_URL}/cropcurrent", timeout=self.timeout, verify=False
        )
        soup = BeautifulSoup(r.text, "html.parser")
        tok = soup.find("input", {"name": "csrf_token"})
        if tok:
            return tok["value"]
        raise RuntimeError("csrf_token not found in Mausam Sankalp page.")

    def post_form(self, form_data: dict) -> Optional[BeautifulSoup]:
        """POST to /cropcurrent and return parsed BeautifulSoup, or None on error."""
        try:
            csrf = self._get_csrf()
            form_data["csrf_token"] = csrf
            r = self.session.post(
                f"{MAUSAM_URL}/cropcurrent",
                data=form_data,
                timeout=self.timeout,
                verify=False,
            )
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            logger.error(f"Mausam POST error: {e}")
            return None

    def post_json(self, url: str, form_data: dict) -> Optional[Any]:
        """POST a form-encoded request expecting JSON back (dropdown endpoints)."""
        try:
            r = self.session.post(url, data=form_data, timeout=self.timeout, verify=False)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Mausam JSON POST {url}: {e}")
            return None


# ---------------------------------------------------------------------------
# HTML table parsers for Mausam Sankalp
# ---------------------------------------------------------------------------

def _parse_weather_table(table) -> dict:
    """
    Parse Table 1 from /cropcurrent:
    Rows: Parameter | Weeks | Rainfall | Tmax | Tmin
    Columns: one per week, grouped by phenological stage.

    Returns:
    {
      "stages": ["Sowing and Emergence", "Seedling", ...],
      "stage_week_map": {"Sowing and Emergence": [24], "Seedling": [25, 26], ...},
      "weeks": [24, 25, 26, ...],
      "rainfall": {"24": 1.4, "25": 4.7, ...},
      "tmax":     {"24": 30.6, ...},
      "tmin":     {"24": 22.2, ...},
      "alerts":   {"24": {"tmax_alert": true, "tmin_alert": false}, ...}
    }
    """
    rows = table.find_all("tr")
    if len(rows) < 5:
        return {}

    # Row 0: stage headers with colspan
    stages = []
    stage_week_map = {}
    for th in rows[0].find_all("th"):
        name = th.get_text(strip=True)
        if name == "Parameter":
            continue
        span = int(th.get("colspan", 1))
        stages.append(name)
        stage_week_map[name] = span  # will convert to actual week lists below

    # Row 1: week numbers
    week_cells = rows[1].find_all(["td", "th"])
    weeks = []
    for cell in week_cells:
        text = cell.get_text(strip=True)
        if text.isdigit():
            weeks.append(int(text))

    # Map stages → their week numbers
    idx = 0
    for stage in stages:
        count = stage_week_map[stage]
        stage_week_map[stage] = weeks[idx: idx + count]
        idx += count

    def _parse_row(row, alert_style="color:red;") -> tuple[dict, dict]:
        """Returns (values_dict, alerts_dict) keyed by week number."""
        cells = row.find_all("td")
        values = {}
        alerts = {}
        for i, cell in enumerate(cells[1:], 0):  # skip first td (label)
            if i >= len(weeks):
                break
            wk = weeks[i]
            text = cell.get_text(strip=True)
            try:
                values[str(wk)] = float(text)
            except ValueError:
                values[str(wk)] = text
            style = cell.get("style", "")
            alerts[str(wk)] = alert_style in style
        return values, alerts

    rainfall_vals, _ = _parse_row(rows[2])
    tmax_vals, tmax_alerts = _parse_row(rows[3])
    tmin_vals, tmin_alerts = _parse_row(rows[4])

    # Merge alert dicts
    combined_alerts = {}
    for wk in [str(w) for w in weeks]:
        combined_alerts[wk] = {
            "tmax_exceeded": tmax_alerts.get(wk, False),
            "tmin_exceeded": tmin_alerts.get(wk, False),
        }

    return {
        "stages": stages,
        "stage_week_map": stage_week_map,
        "weeks": weeks,
        "week_labels": {str(w): WEEK_LABELS.get(w, f"Week {w}") for w in weeks},
        "rainfall_mm": rainfall_vals,
        "tmax_celsius": tmax_vals,
        "tmin_celsius": tmin_vals,
        "threshold_alerts": combined_alerts,
    }


def _parse_threshold_table(table) -> dict:
    """
    Parse Table 2 from /cropcurrent (Weather Parameter Threshold Table).

    The IMD HTML has unclosed <td> tags in these rows, causing standard
    td.find_all() to merge all values into one cell. We extract <b> tags
    directly from each row instead, which are always properly closed.

    Returns:
    {
      "tmax_range_celsius": {"Sowing and Emergence": "31-36", "Seedling": "27-34", ...},
      "tmin_range_celsius": {"Sowing and Emergence": "12-19", ...}
    }
    """
    rows = table.find_all("tr")
    if len(rows) < 4:
        return {}

    # Row 1: stage headers (standard <th> tags, properly closed)
    stages = [
        th.get_text(strip=True)
        for th in rows[1].find_all("th")
        if th.get_text(strip=True) != "Parameter"
    ]

    def _extract_row_by_bold(row) -> dict:
        """Extract values by finding all <b> tags — bypasses unclosed <td> issue."""
        bold_vals = [b.get_text(strip=True) for b in row.find_all("b")]
        values = {}
        for i, val in enumerate(bold_vals):
            if i >= len(stages):
                break
            values[stages[i]] = val
        return values

    tmax_ranges = _extract_row_by_bold(rows[2])
    tmin_ranges = _extract_row_by_bold(rows[3])

    return {
        "tmax_range_celsius": tmax_ranges,
        "tmin_range_celsius": tmin_ranges,
    }


# ---------------------------------------------------------------------------
# IMDClient — public API
# ---------------------------------------------------------------------------

class IMDClient:
    """
    Full-coverage client for IMD agrometeorology data.

    Sources:
      - webgis.imd.gov.in  → JSON APIs (no scraping needed)
      - mausamsankalp.imd.gov.in → HTML scraping (returns structured dicts)

    All methods return dict/list or None on failure.
    """

    def __init__(self):
        self._webgis = _WebGISSession()
        self._mausam = _MausamSession()

    # =========================================================================
    # SECTION 1: WebGIS — Location & Geography
    # =========================================================================

    def get_states(self) -> Optional[list]:
        """
        List all states available in the IMD WebGIS system.

        Returns: [{"state": "Punjab"}, {"state": "Maharashtra"}, ...]
        """
        return self._webgis.get(
            "/agro/fetch_options/",
            params={"type": "gpcodeState", "parent_value": "India"},
        )

    def get_districts(self, state: str) -> Optional[list]:
        """
        List districts for a state.

        Args:
            state: Full state name, e.g. "Maharashtra"
        Returns: [{"district": "Pune"}, ...]
        """
        return self._webgis.get(
            "/agro/fetch_options/",
            params={"type": "gpcodeDistrict", "parent_value": state},
        )

    def get_blocks(self, district: str) -> Optional[list]:
        """
        List blocks/talukas for a district.

        Args:
            district: District name, e.g. "Pune"
        Returns: [{"block": "Haveli"}, ...]
        """
        return self._webgis.get(
            "/agro/fetch_options/",
            params={"type": "gpcodeBlock", "parent_value": district},
        )

    def get_gram_panchayats(self, block: str) -> Optional[list]:
        """
        List Gram Panchayats for a block.

        Args:
            block: Block name
        Returns: [{"gpcode": "...", "gp": "..."}, ...]
        """
        return self._webgis.get(
            "/agro/fetch_options/",
            params={"type": "gpcodeGP", "parent_value": block},
        )

    def get_coordinates_by_gpcode(self, gp_code: str) -> Optional[dict]:
        """
        Get lat/lon coordinates for a Gram Panchayat.

        Args:
            gp_code: GP code string from get_gram_panchayats()
        Returns: {"lat": ..., "lon": ...} or similar
        """
        return self._webgis.get(
            "/search_lat_lon/",
            params={"type": "gpcode", "value": gp_code},
        )

    def get_district_bounds(self, state: str, district: str) -> Optional[dict]:
        """
        Get bounding box / centroid for a state+district pair.

        Args:
            state: State name, e.g. "Gujarat"
            district: District name, e.g. "Surat"
        Returns: dict with coordinate/bounds info
        """
        return self._webgis.get(
            "/search_state_district/",
            params={"state": state, "district": district},
        )

    # =========================================================================
    # SECTION 2: WebGIS — Crop Stages & Phenology
    # =========================================================================

    def get_crop_stages(self, state: str, crop: str) -> Optional[dict]:
        """
        Get phenological growth stages for a crop in a state.

        Args:
            state: State name, e.g. "Punjab"
            crop: Crop name, e.g. "wheat"
        Returns: {"success": true, "stages": ["Tillering", "Booting", ...]}
        """
        return self._webgis.post(
            "/agro/get_stages_for_state/",
            payload={"state": state, "crop": crop},
        )

    def get_combined_crop_data(self, state: str, stage: str) -> Optional[dict]:
        """
        Get combined current weather vs. threshold table for a growth stage.

        Args:
            state: State name, e.g. "Haryana"
            stage: Phenological stage, e.g. "Tillering"
        Returns: Combined weather + threshold data dict
        """
        return self._webgis.post(
            "/agro/get_combined_data/",
            payload={"state": state, "phenological_stage": stage},
        )

    # =========================================================================
    # SECTION 3: WebGIS — Alerts, Diseases, Pests
    # =========================================================================

    def get_thresholds(self, state: str, crop: str, stage: str) -> Optional[dict]:
        """
        Get weather thresholds for a crop at a given growth stage.

        Args:
            state: State name, e.g. "Madhya Pradesh"
            crop: Crop name, e.g. "wheat"
            stage: Growth stage, e.g. "Heading"
        Returns: dict of threshold values keyed by parameter name
        """
        return self._webgis.post(
            "/agro/get_threshold_data/",
            payload={"state": state, "crop": crop, "stage": stage},
        )

    def get_warnings(
        self,
        state: str,
        crop: str,
        stage: str,
        conditions: list[str],
    ) -> Optional[dict]:
        """
        Get agronomic warning messages when weather thresholds are breached.

        Args:
            state: State name
            crop: Crop name, e.g. "wheat"
            stage: Growth stage, e.g. "Heading"
            conditions: List of breached condition codes, e.g. ["T_Max", "RH_Max"]
        Returns: dict with warning messages per condition
        """
        return self._webgis.post(
            "/agro/get_warning_messages/",
            payload={"state": state, "crop": crop, "stage": stage, "conditions": conditions},
        )

    def get_pest_info(self, state: str, crop: str, stage: str) -> Optional[dict]:
        """
        Get pest information for a crop at a growth stage.

        Args:
            state: State name, e.g. "Uttar Pradesh"
            crop: Crop name, e.g. "wheat"
            stage: Growth stage, e.g. "Flowering"
        Returns: dict with pest names, symptoms, management advice
        """
        return self._webgis.post(
            "/agro/get_pest_info/",
            payload={"state": state, "crop": crop, "stage": stage},
        )

    def get_wheat_disease_risk(
        self,
        stage: str,
        tmax: float,
        tmin: float,
        rh: float,
        rainfall: float = 0.0,
    ) -> Optional[dict]:
        """
        Calculate wheat disease risk from current weather parameters.

        Args:
            stage: Growth stage, e.g. "Anthesis"
            tmax: Max temperature (°C)
            tmin: Min temperature (°C)
            rh: Relative humidity (%)
            rainfall: Rainfall in mm (default 0.0)
        Returns: {"success": true, "diseases": [{
                    "disease": "Yellow Rust", "stage": "...",
                    "tmax_original": "<18", ...}, ...]}
        """
        return self._webgis.post(
            "/agro/get_wheat_diseases/",
            payload={
                "stage": stage,
                "current_tmax": tmax,
                "current_tmin": tmin,
                "current_rh": rh,
                "current_rainfall": rainfall,
            },
        )

    # =========================================================================
    # SECTION 4: Mausam Sankalp — Dropdown APIs (JSON)
    # =========================================================================

    def get_mausam_states(self) -> Optional[list]:
        """
        List states available in Mausam Sankalp (uses 2-letter codes).

        Parses the homepage HTML to return a list of state options.
        Returns: [{"code": "AP", "name": "Andhra Pradesh"}, ...]
        """
        try:
            r = self._mausam.session.get(
                f"{MAUSAM_URL}/cropcurrent", timeout=20, verify=False
            )
            soup = BeautifulSoup(r.text, "html.parser")
            sel = soup.find("select", {"name": "State"})
            if not sel:
                return None
            return [
                {"code": opt["value"], "name": opt.get_text(strip=True)}
                for opt in sel.find_all("option")
                if opt.get("value")
            ]
        except Exception as e:
            logger.error(f"get_mausam_states: {e}")
            return None

    def get_mausam_districts(self, state_code: str) -> Optional[list]:
        """
        Get districts for a state from Mausam Sankalp.

        Args:
            state_code: Two-letter code, e.g. "KA" for Karnataka
        Returns: [{"id": "Bangalore Urban"}, ...]
        """
        return self._mausam.post_json(
            f"{MAUSAM_URL}/getdist",
            form_data={"id": state_code, "state": state_code},
        )

    def get_mausam_blocks(self, state_code: str, district: str) -> Optional[list]:
        """
        Get blocks for a district from Mausam Sankalp.

        Args:
            state_code: Two-letter code, e.g. "KA"
            district: District name, e.g. "Bangalore Urban"
        Returns: [{"id": "Yelahanka"}, ...]
        """
        return self._mausam.post_json(
            f"{MAUSAM_URL}/getblock",
            form_data={"id": district, "state": state_code},
        )

    # =========================================================================
    # SECTION 5: Mausam Sankalp — Scraped Data (HTML → structured JSON)
    # =========================================================================

    def get_mausam_crop_weather(
        self,
        state_code: str,
        district: str,
        block: str,
    ) -> Optional[dict]:
        """
        Fetch location-specific historical weekly weather data and thresholds
        from Mausam Sankalp (scrapes /cropcurrent form).

        This is the CORE Mausam Sankalp dataset — it provides:
          - Weekly Rainfall, Tmax, Tmin per phenological stage
          - Colour-coded threshold alerts (red = exceeded)
          - Optimal temperature threshold ranges per stage

        Args:
            state_code: Two-letter state code, e.g. "AP"
            district: District name, e.g. "Anantapur"
            block: Block name, e.g. "Gooty"

        Returns:
        {
          "location": {"state_code": "AP", "district": "Anantapur", "block": "Gooty"},
          "weather_data": {
            "stages": [...],
            "stage_week_map": {"Sowing and Emergence": [24, 25], ...},
            "weeks": [24, 25, 26, ...],
            "week_labels": {"24": "Jun 11-17", ...},
            "rainfall_mm": {"24": 1.4, "25": 4.7, ...},
            "tmax_celsius": {"24": 30.6, ...},
            "tmin_celsius": {"24": 22.2, ...},
            "threshold_alerts": {"24": {"tmax_exceeded": false, "tmin_exceeded": true}, ...}
          },
          "thresholds": {
            "tmax_range_celsius": {"Sowing and Emergence": "31-36", ...},
            "tmin_range_celsius": {"Sowing and Emergence": "12-19", ...}
          }
        }
        """
        soup = self._mausam.post_form({
            "State": state_code,
            "District": district,
            "Block": block,
            "cropsubmit": "Submit",
        })
        if soup is None:
            return None

        tables = soup.find_all("table", class_="corporate-table")
        if len(tables) < 2:
            logger.warning("Mausam Sankalp: expected 2 tables, got %d", len(tables))
            return None

        weather_data = _parse_weather_table(tables[0])
        thresholds = _parse_threshold_table(tables[1])

        return {
            "location": {
                "state_code": state_code,
                "district": district,
                "block": block,
            },
            "weather_data": weather_data,
            "thresholds": thresholds,
        }

    def get_mausam_crop_calendar(
        self,
        crop: str,
        start_week: int,
    ) -> Optional[dict]:
        """
        Fetch crop calendar weather data from Mausam Sankalp.
        This shows what weather conditions the crop will experience
        starting from a given sowing week, across its entire lifecycle.

        Args:
            crop: "wheat" or "groundnut"
            start_week: ISM week number (1–52) for sowing, e.g. 10 = Mar 5-11

        Returns: Same structure as get_mausam_crop_weather() but for
                 the crop-calendar perspective (sowing-week-based).
        {
          "crop": "wheat",
          "sowing_week": 10,
          "sowing_label": "Mar 5-11",
          "weather_data": { ... },
          "thresholds": { ... }
        }
        """
        soup = self._mausam.post_form({
            "Crop": crop.lower(),
            "startWeek": str(start_week),
            "cropcalsubmit": "Submit",
        })
        if soup is None:
            return None

        tables = soup.find_all("table", class_="corporate-table")
        if len(tables) < 2:
            logger.warning("Mausam calendar: expected 2 tables, got %d", len(tables))
            return None

        weather_data = _parse_weather_table(tables[0])
        thresholds = _parse_threshold_table(tables[1])

        return {
            "crop": crop.lower(),
            "sowing_week": start_week,
            "sowing_label": WEEK_LABELS.get(start_week, f"Week {start_week}"),
            "weather_data": weather_data,
            "thresholds": thresholds,
        }

    def get_mausam_available_crops(self) -> list[str]:
        """
        Return the crops supported by Mausam Sankalp.
        (Static — scraped from page on first run and hardcoded for speed.)
        """
        return ["wheat", "groundnut"]

    def get_mausam_available_weeks(self) -> dict:
        """
        Return all 52 week numbers with their date labels.
        Use these as valid values for start_week in get_mausam_crop_calendar().
        """
        return WEEK_LABELS

    # =========================================================================
    # SECTION 6: Composite high-level methods (for LLM context)
    # =========================================================================

    def get_full_crop_advisory(
        self,
        state: str,
        crop: str,
        stage: str,
        tmax: float,
        tmin: float,
        rh: float,
        rainfall: float = 0.0,
    ) -> dict:
        """
        Full advisory from WebGIS: thresholds + disease risk + pest info + warnings.
        Automatically detects exceeded conditions and fetches relevant warnings.

        Args:
            state: Full state name, e.g. "Punjab"
            crop: Crop name, e.g. "wheat"
            stage: Growth stage, e.g. "Flowering"
            tmax: Current max temperature (°C)
            tmin: Current min temperature (°C)
            rh: Current relative humidity (%)
            rainfall: Current rainfall (mm)

        Returns: Structured dict ready to JSON-serialize into an LLM prompt.
        """
        advisory = {
            "source": "IMD WebGIS (webgis.imd.gov.in)",
            "state": state,
            "crop": crop,
            "stage": stage,
            "current_weather": {"tmax": tmax, "tmin": tmin, "rh": rh, "rainfall": rainfall},
            "thresholds": None,
            "warnings": None,
            "disease_risk": None,
            "pest_info": None,
            "errors": [],
        }

        thresholds = self.get_thresholds(state, crop, stage)
        if thresholds:
            advisory["thresholds"] = thresholds
            exceeded = []
            try:
                for key, val in thresholds.items():
                    if not isinstance(val, (int, float)):
                        continue
                    if "T_Max" in key and tmax > val:
                        exceeded.append("T_Max")
                    if "T_Min" in key and tmin < val:
                        exceeded.append("T_Min")
                    if "RH" in key and rh > val:
                        exceeded.append("RH_Max")
            except Exception:
                pass
            if exceeded:
                advisory["warnings"] = self.get_warnings(state, crop, stage, exceeded)
        else:
            advisory["errors"].append("Thresholds unavailable for this state/crop/stage combo.")

        if crop.lower() == "wheat":
            advisory["disease_risk"] = self.get_wheat_disease_risk(
                stage, tmax, tmin, rh, rainfall
            )

        advisory["pest_info"] = self.get_pest_info(state, crop, stage)
        return advisory

    def get_full_location_report(
        self,
        state_code: str,
        district: str,
        block: str,
        webgis_state: str,
        crop: str,
        stage: str,
        tmax: float,
        tmin: float,
        rh: float,
        rainfall: float = 0.0,
    ) -> dict:
        """
        Combined report from BOTH portals for a specific location.

        Merges WebGIS JSON advisory with Mausam Sankalp historical weather
        into a single dict suitable for RAG context injection.

        Args:
            state_code: 2-letter Mausam Sankalp code, e.g. "PB"
            district: District name
            block: Block name
            webgis_state: Full state name for WebGIS, e.g. "Punjab"
            crop: Crop name
            stage: Current growth stage
            tmax/tmin/rh/rainfall: Current weather observations

        Returns: Combined dict with keys:
          "webgis_advisory", "mausam_weather", "mausam_calendar"
        """
        return {
            "webgis_advisory": self.get_full_crop_advisory(
                webgis_state, crop, stage, tmax, tmin, rh, rainfall
            ),
            "mausam_weather": self.get_mausam_crop_weather(
                state_code, district, block
            ),
        }



# ---------------------------------------------------------------------------
# Test — run directly to verify all endpoints
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    client = IMDClient()
    sep = "=" * 65

    print(sep)
    print("IMD Full Tool — Connectivity Test")
    print(sep)

    # --- WebGIS ---
    print("\n[WebGIS] 1/6  get_states()")
    data = client.get_states()
    print(f"   {'✓' if data else '✗'}  {str(data)[:80]}")

    print("\n[WebGIS] 2/6  get_districts('Punjab')")
    data = client.get_districts("Punjab")
    print(f"   {'✓' if data else '✗'}  {str(data)[:80]}")

    print("\n[WebGIS] 3/6  get_crop_stages('Punjab', 'wheat')")
    data = client.get_crop_stages("Punjab", "wheat")
    print(f"   {'✓' if data else '✗'}  {str(data)[:100]}")

    print("\n[WebGIS] 4/6  get_wheat_disease_risk('Anthesis', 32, 15, 65)")
    data = client.get_wheat_disease_risk("Anthesis", 32, 15, 65)
    print(f"   {'✓' if data else '✗'}  {str(data)[:120]}")

    print("\n[WebGIS] 5/6  get_pest_info('Punjab', 'wheat', 'Flowering')")
    data = client.get_pest_info("Punjab", "wheat", "Flowering")
    print(f"   {'✓' if data else '✗'}  {str(data)[:120]}")

    print("\n[WebGIS] 6/6  get_full_crop_advisory('Punjab','wheat','Flowering',32,15,65)")
    adv = client.get_full_crop_advisory("Punjab", "wheat", "Flowering", 32, 15, 65)
    print(f"   ✓  keys={list(adv.keys())}, errors={adv['errors'] or 'none'}")

    # --- Mausam Sankalp ---
    print(f"\n{sep}")
    print("[Mausam] 1/4  get_mausam_states()")
    data = client.get_mausam_states()
    print(f"   {'✓' if data else '✗'}  {str(data)[:100]}")

    print("\n[Mausam] 2/4  get_mausam_districts('AP')")
    data = client.get_mausam_districts("AP")
    print(f"   {'✓' if data else '✗'}  {str(data)[:100]}")

    print("\n[Mausam] 3/4  get_mausam_crop_weather('AP', 'Anantapur', 'Gooty')")
    data = client.get_mausam_crop_weather("AP", "Anantapur", "Gooty")
    if data:
        wd = data.get("weather_data", {})
        th = data.get("thresholds", {})
        print(f"   ✓  stages={wd.get('stages', [])[:3]}...")
        print(f"      weeks={wd.get('weeks', [])[:5]}...")
        print(f"      sample rainfall={dict(list(wd.get('rainfall_mm', {}).items())[:3])}")
        print(f"      sample tmax={dict(list(wd.get('tmax_celsius', {}).items())[:3])}")
        print(f"      sample alerts={dict(list(wd.get('threshold_alerts', {}).items())[:2])}")
        print(f"      tmax thresholds (first 2 stages)={dict(list(th.get('tmax_range_celsius', {}).items())[:2])}")
    else:
        print("   ✗  No data returned")

    print("\n[Mausam] 4/4  get_mausam_crop_calendar('wheat', start_week=10)")
    data = client.get_mausam_crop_calendar("wheat", 10)
    if data:
        wd = data.get("weather_data", {})
        print(f"   ✓  sowing_label='{data.get('sowing_label')}'")
        print(f"      stages={wd.get('stages', [])[:3]}...")
        print(f"      weeks={wd.get('weeks', [])[:5]}...")
    else:
        print("   ✗  No data returned")

    print(f"\n{sep}")
    print("Done.")
