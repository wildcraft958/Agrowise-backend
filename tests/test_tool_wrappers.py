"""Tests for LangChain @tool wrappers around existing tool modules."""

import json
from unittest.mock import patch

from langchain_core.tools import BaseTool

from agromind.agent.tools import (
    ALL_TOOLS,
    cibrc_check_batch,
    cibrc_safety_check,
    evapotranspiration_calc,
    imd_crop_calendar,
    imd_crop_stages,
    imd_mausam_weather,
    imd_weather_check,
    kcc_get_by_state,
    kcc_search,
    soil_moisture_analysis,
)

# ---------------------------------------------------------------------------
# CIBRC tool
# ---------------------------------------------------------------------------

class TestCIBRCSafetyCheck:
    def test_is_langchain_tool(self):
        assert isinstance(cibrc_safety_check, BaseTool)

    def test_name_matches_config(self):
        assert cibrc_safety_check.name == "cibrc_safety_check"

    def test_returns_json_string_on_success(self):
        mock_result = {
            "query": "DDT",
            "status": "BANNED",
            "is_safe_to_recommend": False,
            "advisory": "DDT is banned in India.",
        }
        with patch("agromind.agent.tools._cibrc_client") as mock_client:
            mock_client.check_chemical_safety.return_value = mock_result
            result = cibrc_safety_check.invoke({"chemical_name": "DDT"})
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["status"] == "BANNED"

    def test_handles_client_exception(self):
        with patch("agromind.agent.tools._cibrc_client") as mock_client:
            mock_client.check_chemical_safety.side_effect = RuntimeError("CSV missing")
            result = cibrc_safety_check.invoke({"chemical_name": "DDT"})
        assert "error" in result.lower()


# ---------------------------------------------------------------------------
# IMD tool
# ---------------------------------------------------------------------------

class TestIMDWeatherCheck:
    def test_is_langchain_tool(self):
        assert isinstance(imd_weather_check, BaseTool)

    def test_name_matches_config(self):
        assert imd_weather_check.name == "imd_weather_check"

    def test_returns_json_string(self):
        mock_result = {"success": True, "advisory": "Good sowing conditions."}
        with patch("agromind.agent.tools._imd_client") as mock_client:
            mock_client.get_full_crop_advisory.return_value = mock_result
            result = imd_weather_check.invoke({
                "state": "Punjab",
                "crop": "wheat",
                "stage": "Sowing",
            })
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["success"] is True

    def test_handles_client_exception(self):
        with patch("agromind.agent.tools._imd_client") as mock_client:
            mock_client.get_full_crop_advisory.side_effect = RuntimeError("Network error")
            result = imd_weather_check.invoke({
                "state": "Punjab",
                "crop": "wheat",
                "stage": "Sowing",
            })
        assert "error" in result.lower()


# ---------------------------------------------------------------------------
# KCC tools
# ---------------------------------------------------------------------------

class TestKCCSearch:
    def test_is_langchain_tool(self):
        assert isinstance(kcc_search, BaseTool)

    def test_name(self):
        assert kcc_search.name == "kcc_search"

    def test_returns_json_string(self):
        mock_records = [{"QueryText": "pest on wheat", "KccAns": "Use neem spray"}]
        with patch("agromind.agent.tools._kcc_client") as mock_client:
            mock_client.search_queries.return_value = mock_records
            result = kcc_search.invoke({"keyword": "pest", "state": "Punjab"})
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, list)


class TestKCCGetByState:
    def test_is_langchain_tool(self):
        assert isinstance(kcc_get_by_state, BaseTool)

    def test_name(self):
        assert kcc_get_by_state.name == "kcc_get_by_state"

    def test_returns_json_string(self):
        mock_records = [{"StateName": "Maharashtra", "QueryText": "irrigation query"}]
        with patch("agromind.agent.tools._kcc_client") as mock_client:
            mock_client.get_by_state.return_value = mock_records
            result = kcc_get_by_state.invoke({"state": "Maharashtra"})
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Additional CIBRC tool
# ---------------------------------------------------------------------------

class TestCIBRCCheckBatch:
    def test_is_langchain_tool(self):
        assert isinstance(cibrc_check_batch, BaseTool)

    def test_name(self):
        assert cibrc_check_batch.name == "cibrc_check_batch"

    def test_returns_json_string(self):
        mock_result = {"Mancozeb": {"status": "REGISTERED"}, "Aldrin": {"status": "BANNED"}}
        with patch("agromind.agent.tools._cibrc_client") as mock_client:
            mock_client.check_batch.return_value = mock_result
            result = cibrc_check_batch.invoke({"chemical_names": "Mancozeb, Aldrin"})
        assert isinstance(result, str)
        data = json.loads(result)
        assert "Mancozeb" in data


# ---------------------------------------------------------------------------
# Additional IMD tools
# ---------------------------------------------------------------------------

class TestIMDCropStages:
    def test_is_langchain_tool(self):
        assert isinstance(imd_crop_stages, BaseTool)

    def test_name(self):
        assert imd_crop_stages.name == "imd_crop_stages"

    def test_returns_json_string(self):
        mock_result = {"success": True, "stages": ["Sowing", "Tillering", "Flowering"]}
        with patch("agromind.agent.tools._imd_client") as mock_client:
            mock_client.get_crop_stages.return_value = mock_result
            result = imd_crop_stages.invoke({"state": "Punjab", "crop": "wheat"})
        assert isinstance(result, str)
        data = json.loads(result)
        assert "stages" in data


class TestIMDMausamWeather:
    def test_is_langchain_tool(self):
        assert isinstance(imd_mausam_weather, BaseTool)

    def test_name(self):
        assert imd_mausam_weather.name == "imd_mausam_weather"

    def test_returns_json_string(self):
        mock_result = {"weather_data": {"weeks": [10, 11], "rainfall_mm": {}}}
        with patch("agromind.agent.tools._imd_client") as mock_client:
            mock_client.get_mausam_crop_weather.return_value = mock_result
            result = imd_mausam_weather.invoke({
                "state_code": "PB", "district": "Ludhiana", "block": "Ludhiana"
            })
        assert isinstance(result, str)
        json.loads(result)


class TestIMDCropCalendar:
    def test_is_langchain_tool(self):
        assert isinstance(imd_crop_calendar, BaseTool)

    def test_name(self):
        assert imd_crop_calendar.name == "imd_crop_calendar"

    def test_returns_json_string(self):
        mock_result = {"sowing_label": "Mar 5-11", "weather_data": {}}
        with patch("agromind.agent.tools._imd_client") as mock_client:
            mock_client.get_mausam_crop_calendar.return_value = mock_result
            result = imd_crop_calendar.invoke({"crop": "wheat", "start_week": 10})
        assert isinstance(result, str)
        data = json.loads(result)
        assert "sowing_label" in data


def test_all_tools_count():
    assert len(ALL_TOOLS) == 10  # 2 mandatory + 8 optional


# ---------------------------------------------------------------------------
# Soil moisture tool
# ---------------------------------------------------------------------------

class TestSoilMoistureAnalysis:
    def test_is_langchain_tool(self):
        assert isinstance(soil_moisture_analysis, BaseTool)

    def test_name(self):
        assert soil_moisture_analysis.name == "soil_moisture_analysis"

    def test_returns_json_string(self):
        mock_result = {"records": [{"district": "Jaipur", "soil_moisture": 42.5}], "total": 1}
        with patch("agromind.agent.tools._soil_client") as mock_client:
            mock_client.get_by_district.return_value = mock_result
            result = soil_moisture_analysis.invoke({"state": "Rajasthan", "district": "Jaipur"})
        assert isinstance(result, str)
        json.loads(result)  # must be valid JSON


# ---------------------------------------------------------------------------
# Evapotranspiration tool
# ---------------------------------------------------------------------------

class TestEvapotranspirationCalc:
    def test_is_langchain_tool(self):
        assert isinstance(evapotranspiration_calc, BaseTool)

    def test_name(self):
        assert evapotranspiration_calc.name == "evapotranspiration_calc"

    def test_returns_json_string(self):
        mock_result = {"records": [{"district": "Tumkur", "et": 5.2}], "total": 1}
        with patch("agromind.agent.tools._et_client") as mock_client:
            mock_client.get_by_district.return_value = mock_result
            result = evapotranspiration_calc.invoke({"state": "Karnataka", "district": "Tumkur"})
        assert isinstance(result, str)
        json.loads(result)
