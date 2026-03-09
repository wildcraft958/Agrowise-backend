"""Tests for IMDStationMapper — geo/imd_stations.py."""

import pytest

from agromind.geo.imd_stations import IMDStationMapper


IMD_CSV = "bolbhav-data/IMD Agromet advisory locations.csv"


@pytest.fixture(scope="module")
def mapper():
    return IMDStationMapper(IMD_CSV)


class TestIMDStationMapperLoad:
    def test_loads_without_error(self):
        m = IMDStationMapper(IMD_CSV)
        assert m is not None

    def test_station_count_nonzero(self, mapper):
        assert mapper.total_stations > 0


class TestIMDStationMapperLookup:
    def test_get_imd_code_for_known_district(self, mapper):
        code = mapper.get_imd_code(state="Punjab", district="Ludhiana")
        assert code == "16_1603"

    def test_get_imd_code_case_insensitive(self, mapper):
        code = mapper.get_imd_code(state="PUNJAB", district="ludhiana")
        assert code == "16_1603"

    def test_get_imd_code_unknown_returns_none(self, mapper):
        code = mapper.get_imd_code(state="Punjab", district="NoDistrict")
        assert code is None

    def test_get_station_returns_full_record(self, mapper):
        record = mapper.get_station(state="Punjab", district="Ludhiana")
        assert record is not None
        assert record["imd_code"] == "16_1603"
        assert record["state_id"] == "16"
        assert record["district_id"] == "1603"

    def test_advisory_url_regional(self, mapper):
        url = mapper.get_advisory_url(
            state="Punjab", district="Ludhiana", date="2024-01-15", lang="regional"
        )
        assert "16_1603" in url
        assert "2024-01-15" in url
        assert "Regional" in url

    def test_advisory_url_english(self, mapper):
        url = mapper.get_advisory_url(
            state="Punjab", district="Ludhiana", date="2024-01-15", lang="english"
        )
        assert "16_1603" in url
        assert "English" in url

    def test_advisory_url_unknown_district_returns_none(self, mapper):
        url = mapper.get_advisory_url(
            state="Punjab", district="NoDistrict", date="2024-01-15"
        )
        assert url is None
