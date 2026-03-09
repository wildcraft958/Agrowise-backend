"""
Soil Moisture Tool — data.gov.in
=================================
Fetches daily soil moisture data from the Government of India Open Data portal
(Ministry of Jal Shakti, Dept. of Water Resources, RD & GR).

Dataset : Daily data of Soil Moisture
Resource: 4554a3c8-74e3-4f93-8727-8fd92161e345
License : Government Open Data License - India

Usage:
    from soil_moisture_tool import SoilMoistureClient
    client = SoilMoistureClient(api_key="<your-key>")

    # Single district fetch
    data = client.get_data(state="Rajasthan", district="Jaipur", year="2024", month="6")

    # Summary stats for a state-month
    stats = client.monthly_summary(state="Maharashtra", year="2024", month="7")
"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Public sample key — max 10 records per call.
# Register at https://data.gov.in to get an unlimited key.
_SAMPLE_API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"

_BASE_URL = "https://api.data.gov.in/resource/4554a3c8-74e3-4f93-8727-8fd92161e345"
_MAX_PAGE  = 100   # max records per request for registered keys


class SoilMoistureClient:
    """
    Query daily soil moisture records from the data.gov.in portal.

    Each record contains soil moisture readings for a district on a specific date,
    measured by a government agency (typically CGWB or state water boards).

    Fields returned per record:
        Year, Month, State, District, Agency_name,
        plus date-wise moisture values (format varies by dataset revision).
    """

    def __init__(self, api_key: str = _SAMPLE_API_KEY, timeout: int = 15):
        """
        Args:
            api_key : data.gov.in API key.  The default sample key returns at most
                      10 records per call and may be rate-limited.
            timeout : HTTP request timeout in seconds.
        """
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; AgroWise/1.0; "
                "+https://github.com/NamoFans-AgroWise)"
            ),
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Core fetch
    # ------------------------------------------------------------------

    def get_data(
        self,
        state:       Optional[str] = None,
        district:    Optional[str] = None,
        year:        Optional[str] = None,
        month:       Optional[str] = None,
        agency_name: Optional[str] = None,
        offset:      int = 0,
        limit:       int = 10,
        fmt:         str = "json",
    ) -> Dict[str, Any]:
        """
        Fetch soil moisture records with optional filters.

        Args:
            state       : State name, e.g. "Rajasthan"
            district    : District name, e.g. "Jaipur"
            year        : 4-digit year string, e.g. "2024"
            month       : Month number string, e.g. "6" or "06"
            agency_name : Measuring agency, e.g. "CGWB"
            offset      : Records to skip (pagination)
            limit       : Records to return (max 10 for sample key)
            fmt         : Response format — "json" (default), "xml", or "csv"

        Returns:
            Parsed JSON dict on success, or {"error": ..., "status_code": ...} on failure.
        """
        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format":  fmt,
            "offset":  offset,
            "limit":   limit,
        }
        if state:
            params["filters[State]"] = state
        if district:
            params["filters[District]"] = district
        if year:
            params["filters[Year]"] = year
        if month:
            params["filters[Month]"] = month
        if agency_name:
            params["filters[Agency_name]"] = agency_name

        try:
            resp = self._session.get(_BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            logger.error("Soil moisture API HTTP %s: %s", e.response.status_code, e.response.text[:200])
            return {"error": str(e), "status_code": e.response.status_code}
        except requests.RequestException as e:
            logger.error("Soil moisture API request failed: %s", e)
            return {"error": str(e)}
        except ValueError as e:
            logger.error("Soil moisture API JSON parse error: %s", e)
            return {"error": f"JSON parse error: {e}"}

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def get_by_district(
        self,
        state:    str,
        district: str,
        year:     Optional[str] = None,
        month:    Optional[str] = None,
        limit:    int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Return records list for a specific state + district.

        Args:
            state    : e.g. "Maharashtra"
            district : e.g. "Pune"
            year     : optional 4-digit year filter
            month    : optional month number filter
            limit    : max records (default 10)

        Returns:
            List of record dicts, empty list on error.
        """
        resp = self.get_data(state=state, district=district, year=year, month=month, limit=limit)
        return resp.get("records", [])

    def get_by_state(
        self,
        state: str,
        year:  Optional[str] = None,
        month: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Return records list for all districts in a state.

        Args:
            state : e.g. "Punjab"
            year  : optional 4-digit year filter
            month : optional month number filter
            limit : max records (default 10)

        Returns:
            List of record dicts, empty list on error.
        """
        resp = self.get_data(state=state, year=year, month=month, limit=limit)
        return resp.get("records", [])

    def monthly_summary(
        self,
        state:    str,
        year:     str,
        month:    str,
        limit:    int = 10,
    ) -> Dict[str, Any]:
        """
        Aggregate soil moisture metadata for a state in a given month.

        Returns a summary dict with:
            state, year, month, total_records, districts, agencies

        Note: With the sample API key, at most 10 records are returned, so district
        and agency lists may be incomplete.  Use a registered key for full coverage.
        """
        resp = self.get_data(state=state, year=year, month=month, limit=limit)
        records = resp.get("records", [])
        total   = resp.get("total", len(records))

        districts = sorted({r.get("District", "").strip() for r in records if r.get("District")})
        agencies  = sorted({r.get("Agency_name", "").strip() for r in records if r.get("Agency_name")})

        return {
            "state":         state,
            "year":          year,
            "month":         month,
            "total_records": total,
            "records_fetched": len(records),
            "districts":     districts,
            "agencies":      agencies,
            "note": (
                "Sample key limited to 10 records per call. "
                "Register at data.gov.in for full dataset access."
            ) if self.api_key == _SAMPLE_API_KEY else None,
        }

    def count(
        self,
        state:    Optional[str] = None,
        district: Optional[str] = None,
        year:     Optional[str] = None,
        month:    Optional[str] = None,
    ) -> int:
        """
        Return the total number of records matching the filters (from API metadata).
        Does not download the actual records (limit=1 to minimize transfer).
        """
        resp = self.get_data(state=state, district=district, year=year, month=month, limit=1)
        return int(resp.get("total", 0))

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def dump_json(self, data: Any) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)



# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    client = SoilMoistureClient()

    print("=" * 60)
    print("Soil Moisture Tool — Self Test")
    print("(Using sample API key — max 10 records per call)")
    print("=" * 60)

    # Test 1: Raw fetch with no filters (should return up to 10 records)
    print("\n[1] Raw fetch (no filters, limit=5)")
    resp = client.get_data(limit=5)
    records = resp.get("records", [])
    total   = resp.get("total", "?")
    print(f"    Total records in dataset : {total}")
    print(f"    Records returned         : {len(records)}")
    if records:
        sample = records[0]
        print(f"    Sample keys              : {list(sample.keys())}")
        print(f"    Sample record            : {sample}")

    # Test 2: Filter by state
    print("\n[2] Filter by State='Rajasthan', limit=3")
    rows = client.get_by_state("Rajasthan", limit=3)
    print(f"    Records returned : {len(rows)}")
    for r in rows:
        print(f"    {r}")

    # Test 3: Filter by state + month
    print("\n[3] Filter by State='Maharashtra', Month='1', limit=3")
    rows = client.get_by_state("Maharashtra", month="1", limit=3)
    print(f"    Records returned : {len(rows)}")
    for r in rows:
        print(f"    {r}")

    # Test 4: Monthly summary
    print("\n[4] Monthly summary — Rajasthan / Year=2022 / Month=1")
    summary = client.monthly_summary("Rajasthan", "2022", "1")
    print(client.dump_json(summary))

    # Test 5: count()
    print("\n[5] Record count (all data)")
    n = client.count()
    print(f"    Total records in dataset: {n}")

    print("\nSelf-test complete.")
