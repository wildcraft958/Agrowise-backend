"""Tests for MandiLocator — geo/mandi_locator.py."""

import pytest

from agromind.geo.mandi_locator import MandiLocator


MANDIS_CSV = "bolbhav-data/Agmark Mandis and locations.csv"
APMC_CSV = "bolbhav-data/Mandi (APMC) Map.csv"


@pytest.fixture(scope="module")
def locator():
    return MandiLocator(mandis_csv=MANDIS_CSV, apmc_csv=APMC_CSV)


class TestMandiLocatorLoad:
    def test_loads_without_error(self):
        m = MandiLocator(mandis_csv=MANDIS_CSV, apmc_csv=APMC_CSV)
        assert m is not None

    def test_mandi_count_nonzero(self, locator):
        assert locator.total_mandis > 0


class TestMandiLocatorLookup:
    def test_get_mandis_by_state(self, locator):
        mandis = locator.get_mandis_by_state("Punjab")
        assert isinstance(mandis, list)
        assert len(mandis) > 0

    def test_get_mandis_by_district_id(self, locator):
        # Ludhiana district ID is 1603
        mandis = locator.get_mandis_by_district_id("1603")
        assert isinstance(mandis, list)

    def test_mandi_record_has_name(self, locator):
        mandis = locator.get_mandis_by_state("Punjab")
        assert all("mandi_name" in m for m in mandis)

    def test_get_mandis_unknown_state_returns_empty(self, locator):
        mandis = locator.get_mandis_by_state("NoSuchState")
        assert mandis == []

    def test_get_apmc_mandis_by_state(self, locator):
        mandis = locator.get_apmc_mandis_by_state("Punjab")
        assert isinstance(mandis, list)
        assert len(mandis) > 0

    def test_apmc_record_has_name_and_code(self, locator):
        mandis = locator.get_apmc_mandis_by_state("Punjab")
        assert all("mandi_name" in m and "mandi_code" in m for m in mandis)
