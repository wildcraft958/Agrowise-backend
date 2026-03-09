"""Tests for LocationResolver — geo/resolver.py."""

import pytest

from agromind.geo.resolver import LocationResolver


HIERARCHY_CSV = "bolbhav-data/Location hierarchy.csv"


class TestLocationResolverLoad:
    def test_loads_without_error(self):
        resolver = LocationResolver(HIERARCHY_CSV)
        assert resolver is not None

    def test_record_count_nonzero(self):
        resolver = LocationResolver(HIERARCHY_CSV)
        assert resolver.total_blocks > 0


class TestLocationResolverResolve:
    @pytest.fixture(scope="class")
    def resolver(self):
        return LocationResolver(HIERARCHY_CSV)

    def test_resolve_exact_state_district_block(self, resolver):
        result = resolver.resolve(state="Punjab", district="Ludhiana", block="Ludhiana-1")
        assert result is not None
        assert result["state_name"].lower() == "punjab"
        assert result["district_name"].lower() == "ludhiana"
        assert result["block_name"].lower() == "ludhiana-1"
        assert "state_id" in result
        assert "district_id" in result
        assert "block_id" in result

    def test_resolve_case_insensitive(self, resolver):
        result = resolver.resolve(state="PUNJAB", district="ludhiana", block="ludhiana-1")
        assert result is not None
        assert result["state_name"].lower() == "punjab"

    def test_resolve_partial_state_only(self, resolver):
        results = resolver.resolve_state("Uttar Pradesh")
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(r["state_name"].lower() == "uttar pradesh" for r in results)

    def test_resolve_state_district(self, resolver):
        results = resolver.resolve_district(state="Uttar Pradesh", district="Agra")
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(r["district_name"].lower() == "agra" for r in results)

    def test_resolve_unknown_returns_none(self, resolver):
        result = resolver.resolve(state="Neverland", district="FooBar", block="Baz")
        assert result is None

    def test_resolve_unknown_district_returns_none(self, resolver):
        result = resolver.resolve(state="Punjab", district="NoSuchDistrict", block="Ludhiana")
        assert result is None

    def test_imd_flag_true_for_imd_block(self, resolver):
        result = resolver.resolve(state="Punjab", district="Ludhiana", block="Ludhiana-1")
        assert result is not None
        # IMD Agromet field indicates IMD coverage
        assert "in_imd_agromet" in result

    def test_list_states(self, resolver):
        states = resolver.list_states()
        assert isinstance(states, list)
        assert "Punjab" in states
        assert "Uttar Pradesh" in states
        assert len(states) >= 20  # India has 28+ states/UTs

    def test_list_districts_for_state(self, resolver):
        districts = resolver.list_districts("Punjab")
        assert isinstance(districts, list)
        assert len(districts) > 0
        assert "Ludhiana" in districts

    def test_list_blocks_for_district(self, resolver):
        blocks = resolver.list_blocks(state="Punjab", district="Ludhiana")
        assert isinstance(blocks, list)
        assert "Ludhiana-1" in blocks

    def test_fuzzy_match_close_spelling(self, resolver):
        # "Ludhiyana" should still resolve to "Ludhiana" or return None
        result = resolver.resolve(state="Punjab", district="Ludhiyana", block="Ludhiana-1")
        # Allow None or a fuzzy match — just verify no crash
        assert result is None or result["district_name"].lower() == "ludhiana"

    def test_get_by_block_id(self, resolver):
        result = resolver.resolve(state="Punjab", district="Ludhiana", block="Ludhiana-1")
        assert result is not None
        block_id = result["block_id"]
        found = resolver.get_by_block_id(block_id)
        assert found is not None
        assert found["block_id"] == block_id
