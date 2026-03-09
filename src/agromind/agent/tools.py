"""LangChain @tool wrappers around the existing standalone tool modules.

Each tool:
- Has snake_case name matching config.yaml (mandatory/optional lists)
- Accepts typed args (Gemini uses these for schema generation)
- Returns a JSON string (models handle strings best)
- Catches all exceptions and returns {"error": ...} JSON so the agent
  can report failure rather than crash

Clients are singletons, instantiated once at import time.
"""

import json
import sys
from pathlib import Path

from langchain_core.tools import tool

# Make tools/ importable from src/agromind/agent/tools.py
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agromind.config import settings  # noqa: E402
from tools.cibrc_tool import CIBRCClient  # noqa: E402
from tools.evapotranspiration_tool import EvapotranspirationClient  # noqa: E402
from tools.imd_tool import IMDClient  # noqa: E402
from tools.kcc_tool import KCCClient  # noqa: E402
from tools.soil_moisture_tool import SoilMoistureClient  # noqa: E402

# ---------------------------------------------------------------------------
# Singleton clients (loaded once at startup)
# ---------------------------------------------------------------------------

_cibrc_client = CIBRCClient(db_path=settings.safety.cibrc_csv_path)
_imd_client = IMDClient()
_kcc_client = KCCClient(api_key=settings.data_gov_api_key or None)
_soil_client = SoilMoistureClient(api_key=settings.data_gov_api_key or None)
_et_client = EvapotranspirationClient(api_key=settings.data_gov_api_key or None)


def _to_json(obj: object) -> str:
    """Serialize any object to a JSON string."""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps({"result": str(obj)})


# ---------------------------------------------------------------------------
# MANDATORY TOOLS
# ---------------------------------------------------------------------------


@tool
def cibrc_safety_check(chemical_name: str) -> str:
    """Check whether an agricultural chemical is banned, restricted, or safe to use in India.

    Uses the CIBRC (Central Insecticides Board & Registration Committee) database.
    Always call this tool before recommending any pesticide, herbicide, or fungicide.

    Args:
        chemical_name: Name of the chemical, e.g. "DDT", "Azoxystrobin", "Neem Oil"

    Returns:
        JSON string with keys: status, is_safe_to_recommend, advisory,
        restriction_details, formulations_available.
    """
    try:
        result = _cibrc_client.check_chemical_safety(chemical_name)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e), "chemical_name": chemical_name})


@tool
def imd_weather_check(
    state: str,
    crop: str,
    stage: str,
    max_temp: float | None = None,
    min_temp: float | None = None,
    humidity: float | None = None,
) -> str:
    """Get IMD agronomic weather advisory for a crop at a specific growth stage.

    Fetches real-time weather data and pest/disease risk from the IMD WebGIS API.
    Always call this tool when answering questions about weather, irrigation timing,
    sowing windows, or climate-related crop management.

    Args:
        state: Indian state name, e.g. "Punjab", "Maharashtra"
        crop: Crop name, e.g. "wheat", "rice", "cotton"
        stage: Phenological growth stage, e.g. "Sowing", "Tillering", "Flowering"
        max_temp: Current maximum temperature in °C (optional, improves advisory)
        min_temp: Current minimum temperature in °C (optional)
        humidity: Current relative humidity % (optional)

    Returns:
        JSON string with weather advisory, thresholds, pest/disease risks.
    """
    try:
        result = _imd_client.get_full_crop_advisory(
            state=state,
            crop=crop,
            stage=stage,
            max_temp=max_temp,
            min_temp=min_temp,
            humidity=humidity,
        )
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e), "state": state, "crop": crop})


# ---------------------------------------------------------------------------
# OPTIONAL TOOLS
# ---------------------------------------------------------------------------


@tool
def kcc_search(keyword: str, state: str | None = None, limit: int = 10) -> str:
    """Search KCC (Kisan Call Centre) farmer query transcripts by keyword.

    Returns real farmer questions and expert answers from the KCC database,
    filtered by keyword. Use this for crop-specific or pest-specific queries
    where local farmer experience is relevant.

    Args:
        keyword: Search term, e.g. "stem borer", "wheat irrigation", "urea dose"
        state: Filter by Indian state name (optional), e.g. "Uttar Pradesh"
        limit: Maximum number of records to return (default 10)

    Returns:
        JSON array of matching KCC transcript records.
    """
    try:
        records = _kcc_client.search_queries(keyword=keyword, state=state, limit=limit)
        return _to_json(records)
    except Exception as e:
        return _to_json({"error": str(e), "keyword": keyword})


@tool
def kcc_get_by_state(
    state: str,
    year: str | None = None,
    month: str | None = None,
    limit: int = 10,
) -> str:
    """Fetch recent KCC farmer queries from a specific Indian state.

    Retrieves farmer questions and expert answers from the Kisan Call Centre
    for a given state, optionally filtered by year and month.

    Args:
        state: Indian state name, e.g. "Bihar", "Andhra Pradesh"
        year: 4-digit year string, e.g. "2024" (optional)
        month: Month number string, e.g. "6" for June (optional)
        limit: Maximum records to return (default 10)

    Returns:
        JSON array of KCC transcript records for the state.
    """
    try:
        records = _kcc_client.get_by_state(state=state, year=year, month=month, limit=limit)
        return _to_json(records)
    except Exception as e:
        return _to_json({"error": str(e), "state": state})


@tool
def soil_moisture_analysis(
    state: str,
    district: str | None = None,
    year: str | None = None,
    month: str | None = None,
) -> str:
    """Retrieve soil moisture data for a district or state.

    Fetches measured soil moisture readings from government monitoring stations.
    Use this to advise on irrigation scheduling or drought stress assessment.

    Args:
        state: Indian state name, e.g. "Rajasthan", "Gujarat"
        district: District name within the state (optional), e.g. "Jaipur"
        year: 4-digit year string, e.g. "2024" (optional)
        month: Month number string, e.g. "3" for March (optional)

    Returns:
        JSON with soil moisture records and summary statistics.
    """
    try:
        if district:
            result = _soil_client.get_by_district(
                state=state, district=district, year=year, month=month
            )
        else:
            result = _soil_client.get_by_state(state=state, year=year, month=month)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e), "state": state, "district": district})


@tool
def evapotranspiration_calc(
    state: str,
    district: str | None = None,
    year: str | None = None,
    month: str | None = None,
) -> str:
    """Retrieve evapotranspiration (ET) data to calculate crop water requirements.

    Fetches ET measurements from government monitoring stations.
    Use this to estimate irrigation water needs, especially for water-sensitive crops.

    Args:
        state: Indian state name, e.g. "Karnataka", "Tamil Nadu"
        district: District name (optional), e.g. "Tumkur"
        year: 4-digit year string, e.g. "2023" (optional)
        month: Month number string, e.g. "7" for July (optional)

    Returns:
        JSON with evapotranspiration records and water requirement estimates.
    """
    try:
        if district:
            result = _et_client.get_by_district(
                state=state, district=district, year=year, month=month
            )
        else:
            result = _et_client.get_by_state(state=state, year=year, month=month)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e), "state": state, "district": district})


@tool
def cibrc_check_batch(chemical_names: str) -> str:
    """Check multiple agricultural chemicals at once against the CIBRC database.

    Use this when a recommendation involves several chemicals and you need to
    verify all of them in one call.

    Args:
        chemical_names: Comma-separated chemical names,
            e.g. "Mancozeb, Chlorpyrifos, Neem Oil"

    Returns:
        JSON object mapping each chemical name to its safety status.
    """
    try:
        names = [n.strip() for n in chemical_names.split(",") if n.strip()]
        result = _cibrc_client.check_batch(names)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e), "chemical_names": chemical_names})


@tool
def imd_crop_stages(state: str, crop: str) -> str:
    """Get the phenological growth stages for a crop in an Indian state.

    Use this to understand what growth stages are available before calling
    imd_weather_check, or when the farmer mentions a specific crop stage.

    Args:
        state: Indian state name, e.g. "Punjab", "Uttar Pradesh"
        crop: Crop name, e.g. "wheat", "rice", "cotton"

    Returns:
        JSON with list of growth stages for the crop in that state.
    """
    try:
        result = _imd_client.get_crop_stages(state=state, crop=crop)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e), "state": state, "crop": crop})


@tool
def imd_mausam_weather(
    state_code: str,
    district: str,
    block: str,
) -> str:
    """Get historical weekly weather data and thresholds for a specific block from Mausam Sankalp.

    Returns actual observed weather (rainfall, Tmax, Tmin) week-by-week alongside
    crop-stage thresholds and alerts. Use this for detailed local weather history
    when the farmer provides a specific district and block.

    Args:
        state_code: 2-letter IMD state code, e.g. "PB" for Punjab, "AP" for Andhra Pradesh
        district: District name, e.g. "Ludhiana", "Anantapur"
        block: Block/taluk name, e.g. "Gooty", "Ludhiana"

    Returns:
        JSON with weekly weather data, growth stages, and threshold alerts.
    """
    try:
        result = _imd_client.get_mausam_crop_weather(
            state_code=state_code, district=district, block=block
        )
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e), "state_code": state_code, "district": district})


@tool
def imd_crop_calendar(crop: str, start_week: int) -> str:
    """Get a crop lifecycle weather calendar from Mausam Sankalp based on sowing week.

    Returns week-by-week weather data aligned to the crop's growth calendar from
    the sowing week. Use this when a farmer wants to plan for an upcoming season
    or compare their crop's progress against expected conditions.

    Args:
        crop: Crop name as recognised by IMD Mausam Sankalp, e.g. "wheat", "rice"
        start_week: ISM calendar week number of sowing (1–52), e.g. 10 for Mar 5–11

    Returns:
        JSON with crop lifecycle calendar, weekly weather, and stage-wise thresholds.
    """
    try:
        result = _imd_client.get_mausam_crop_calendar(crop=crop, start_week=start_week)
        return _to_json(result)
    except Exception as e:
        return _to_json({"error": str(e), "crop": crop, "start_week": start_week})


# ---------------------------------------------------------------------------
# All tools list (for bind_tools and enforcement checks)
# ---------------------------------------------------------------------------

MANDATORY_TOOLS = [cibrc_safety_check, imd_weather_check]
OPTIONAL_TOOLS = [
    cibrc_check_batch,
    kcc_search,
    kcc_get_by_state,
    soil_moisture_analysis,
    evapotranspiration_calc,
    imd_crop_stages,
    imd_mausam_weather,
    imd_crop_calendar,
]
ALL_TOOLS = MANDATORY_TOOLS + OPTIONAL_TOOLS
