"""Agmarknet live mandi price client.

Fetches daily wholesale (mandi) prices from the Agmarknet dataset on data.gov.in.

Dataset: "Current Daily Price of Various Commodities from various Markets"
Resource ID: 9ef84268-d588-465a-a308-a864a43d0070
API base: https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070

Each record contains:
    state, district, market, commodity, variety,
    min_price, max_price, modal_price, arrival_date

Usage:
    client = AgmarknetClient(api_key="<data.gov.in key>")
    prices = client.get_prices(state="Punjab", commodity="Wheat")
    latest = client.get_latest_price(state="Punjab", commodity="Wheat")
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
_BASE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
_DEFAULT_LIMIT = 50


class AgmarknetClient:
    """Fetches live mandi prices from Agmarknet via data.gov.in."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or _SAMPLE_KEY

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_prices(
        self,
        state: str,
        commodity: str,
        market: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """Return mandi price records for a state + commodity.

        Args:
            state: Indian state name, e.g. "Punjab".
            commodity: Commodity name, e.g. "Wheat", "Rice".
            market: Optional mandi/market name to filter results.
            limit: Maximum records to return.

        Returns:
            List of price record dicts (empty on error or no data).
        """
        if not commodity.strip():
            return []

        try:
            records = self._fetch_records(state=state, commodity=commodity, limit=limit)
        except Exception as exc:
            logger.warning("Agmarknet get_prices error: %s", exc)
            return []

        if market:
            ml = market.strip().lower()
            records = [r for r in records if r.get("market", "").lower() == ml]

        return records

    def get_latest_price(
        self,
        state: str,
        commodity: str,
        market: str | None = None,
    ) -> dict[str, Any] | None:
        """Return the most recent price record for a commodity, or None."""
        records = self.get_prices(state=state, commodity=commodity, market=market, limit=10)
        if not records:
            return None
        # Records are typically ordered by date desc; return first
        return records[0]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_records(
        self,
        state: str,
        commodity: str,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """Call the data.gov.in API and return normalized records."""
        params: dict[str, Any] = {
            "api-key": self._api_key,
            "format": "json",
            "limit": limit,
            "filters[state.keyword]": state,
            "filters[commodity]": commodity,
        }
        response = httpx.get(_BASE_URL, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        raw = data.get("records", [])
        return [self._normalize(r) for r in raw]

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw API record to consistent snake_case keys."""
        return {
            "state": raw.get("state", ""),
            "district": raw.get("district", ""),
            "market": raw.get("market", ""),
            "commodity": raw.get("commodity", ""),
            "variety": raw.get("variety", ""),
            "min_price": _to_float(raw.get("min_price", 0)),
            "max_price": _to_float(raw.get("max_price", 0)),
            "modal_price": _to_float(raw.get("modal_price", 0)),
            "arrival_date": raw.get("arrival_date", ""),
        }


def _to_float(val: Any) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
