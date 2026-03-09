"""Tests for AgmarknetClient — market/agmarknet.py."""

from unittest.mock import MagicMock, patch

import pytest

from agromind.market.agmarknet import AgmarknetClient


@pytest.fixture
def client():
    return AgmarknetClient(api_key=None)


class TestAgmarknetClientInit:
    def test_instantiates_without_key(self):
        c = AgmarknetClient(api_key=None)
        assert c is not None

    def test_instantiates_with_key(self):
        c = AgmarknetClient(api_key="test-key")
        assert c is not None


class TestGetPrices:
    def test_returns_list_of_dicts(self, client):
        mock_records = [
            {
                "state": "Punjab",
                "market": "Ludhiana",
                "commodity": "Wheat",
                "min_price": 2100.0,
                "max_price": 2200.0,
                "modal_price": 2150.0,
                "arrival_date": "2024-01-15",
            }
        ]
        with patch.object(client, "_fetch_records", return_value=mock_records):
            result = client.get_prices(state="Punjab", commodity="Wheat")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["commodity"] == "Wheat"

    def test_returns_empty_on_api_error(self, client):
        with patch.object(client, "_fetch_records", side_effect=RuntimeError("API down")):
            result = client.get_prices(state="Punjab", commodity="Wheat")
        assert result == []

    def test_filters_by_market(self, client):
        mock_records = [
            {"market": "Ludhiana", "commodity": "Wheat", "modal_price": 2150.0},
            {"market": "Jalandhar", "commodity": "Wheat", "modal_price": 2100.0},
        ]
        with patch.object(client, "_fetch_records", return_value=mock_records):
            result = client.get_prices(state="Punjab", commodity="Wheat", market="Ludhiana")

        assert all(r["market"] == "Ludhiana" for r in result)

    def test_empty_commodity_returns_empty(self, client):
        result = client.get_prices(state="Punjab", commodity="")
        assert result == []


class TestGetLatestPrice:
    def test_returns_dict_for_known_commodity(self, client):
        mock_records = [
            {"modal_price": 2150.0, "arrival_date": "2024-01-15", "market": "Ludhiana"},
            {"modal_price": 2100.0, "arrival_date": "2024-01-14", "market": "Ludhiana"},
        ]
        with patch.object(client, "_fetch_records", return_value=mock_records):
            result = client.get_latest_price(state="Punjab", commodity="Wheat")

        assert result is not None
        assert "modal_price" in result

    def test_returns_none_when_no_records(self, client):
        with patch.object(client, "_fetch_records", return_value=[]):
            result = client.get_latest_price(state="Punjab", commodity="XYZGrain")
        assert result is None

    def test_result_has_price_keys(self, client):
        mock_records = [{
            "min_price": 2100.0,
            "max_price": 2200.0,
            "modal_price": 2150.0,
            "arrival_date": "2024-01-15",
            "market": "Ludhiana",
            "commodity": "Wheat",
        }]
        with patch.object(client, "_fetch_records", return_value=mock_records):
            result = client.get_latest_price(state="Punjab", commodity="Wheat")
        assert result is not None
        assert "min_price" in result
        assert "max_price" in result
        assert "modal_price" in result
