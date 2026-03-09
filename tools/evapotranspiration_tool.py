"""
Evapotranspiration Tool — data.gov.in
======================================
Fetches daily evapotranspiration (ET) data from the Government of India Open Data
portal, published by NRSC (National Remote Sensing Centre).

Dataset : Daily data of Evapotranspiration of NRSC
Resource: 98c433b1-9c86-40c7-baf4-d4eca5385698
Ministry : Jal Shakti, Department of Water Resources, RD & GR
License  : Government Open Data License - India

Evapotranspiration (ET) is the combined water loss from soil evaporation and
plant transpiration.  High ET indicates crop water stress; it is the primary
input for irrigation scheduling and crop water-requirement models.

Usage:
    from evapotranspiration_tool import EvapotranspirationClient
    client = EvapotranspirationClient(api_key="<your-key>")

    records = client.get_by_district("Karnataka", "Tumkur", year="2022", month="8")
    summary = client.monthly_summary("Maharashtra", "2022", "8")
"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Public sample key — max 10 records per call.
# Register at https://data.gov.in to get an unlimited key.
_SAMPLE_API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"

_BASE_URL = "https://api.data.gov.in/resource/98c433b1-9c86-40c7-baf4-d4eca5385698"


class EvapotranspirationClient:
    """
    Query daily evapotranspiration records from the data.gov.in portal.

    Each record contains ET values (mm/day) for a district on a specific date,
    derived from NRSC satellite remote-sensing products.

    Fields returned per record (vary by dataset revision):
        Year, Month, State, District, Agency_name,
        plus date-wise ET values.
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
        Fetch evapotranspiration records with optional filters.

        Args:
            state       : State name, e.g. "Karnataka"
            district    : District name, e.g. "Tumkur"
            year        : 4-digit year string, e.g. "2022"
            month       : Month number string, e.g. "8" or "08"
            agency_name : Measuring agency, e.g. "NRSC"
            offset      : Records to skip (pagination)
            limit       : Records to return (max 10 for sample key)
            fmt         : "json" (default), "xml", or "csv"

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
            logger.error("ET API HTTP %s: %s", e.response.status_code, e.response.text[:200])
            return {"error": str(e), "status_code": e.response.status_code}
        except requests.RequestException as e:
            logger.error("ET API request failed: %s", e)
            return {"error": str(e)}
        except ValueError as e:
            logger.error("ET API JSON parse error: %s", e)
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
        Return ET records for a specific state + district.

        Args:
            state    : e.g. "Karnataka"
            district : e.g. "Tumkur"
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
        Return ET records for all districts in a state.

        Args:
            state : e.g. "Maharashtra"
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
        state: str,
        year:  str,
        month: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Aggregate ET metadata for a state in a given month.

        Returns a summary dict with:
            state, year, month, total_records, records_fetched, districts, agencies

        Note: With the sample API key, at most 10 records are returned per call.
        Use a registered key for full coverage.
        """
        resp     = self.get_data(state=state, year=year, month=month, limit=limit)
        records  = resp.get("records", [])
        total    = resp.get("total", len(records))

        districts = sorted({r.get("District", "").strip() for r in records if r.get("District")})
        agencies  = sorted({r.get("Agency_name", "").strip() for r in records if r.get("Agency_name")})

        return {
            "state":           state,
            "year":            year,
            "month":           month,
            "total_records":   total,
            "records_fetched": len(records),
            "districts":       districts,
            "agencies":        agencies,
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
        Return total matching records from API metadata (limit=1 to minimise transfer).
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
    client = EvapotranspirationClient()

    print("=" * 60)
    print("Evapotranspiration Tool — Self Test")
    print("(Using sample API key — max 10 records per call)")
    print("=" * 60)

    # Test 1: Raw fetch (no filters)
    print("\n[1] Raw fetch (no filters, limit=5)")
    resp    = client.get_data(limit=5)
    records = resp.get("records", [])
    total   = resp.get("total", "?")
    print(f"    Total records in dataset : {total}")
    print(f"    Records returned         : {len(records)}")
    if records:
        sample = records[0]
        print(f"    Sample keys              : {list(sample.keys())}")
        print(f"    Sample record            : {sample}")

    # Test 2: Filter by state
    print("\n[2] Filter by State='Karnataka', limit=3")
    rows = client.get_by_state("Karnataka", limit=3)
    print(f"    Records returned : {len(rows)}")
    for r in rows:
        print(f"    {r}")

    # Test 3: Filter by state + month
    print("\n[3] Filter by State='Maharashtra', Month='8', limit=3")
    rows = client.get_by_state("Maharashtra", month="8", limit=3)
    print(f"    Records returned : {len(rows)}")
    for r in rows:
        print(f"    {r}")

    # Test 4: Monthly summary
    print("\n[4] Monthly summary — Karnataka / Year=2022 / Month=8")
    summary = client.monthly_summary("Karnataka", "2022", "8")
    print(client.dump_json(summary))

    # Test 5: count()
    print("\n[5] Total record count (all data)")
    n = client.count()
    print(f"    Total records in dataset: {n}")

    print("\nSelf-test complete.")
