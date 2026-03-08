"""
Kisan Call Centre (KCC) Tool — data.gov.in
===========================================
Fetches farmer query transcripts from the Kisan Call Centre (KCC) dataset
published by the Ministry of Agriculture and Farmers Welfare on data.gov.in.

Dataset : Kisan Call Centre (KCC) — Transcripts of farmers queries & answers
Resource: cef25fe2-9231-4128-8aec-2c948fedd43f
Ministry : Agriculture and Farmers Welfare, Dept. of Agriculture and Farmers Welfare
License  : Government Open Data License - India

KCC is India's 24×7 toll-free agricultural helpline (1800-180-1551).  The dataset
contains real farmer questions and expert answers, organized by state, month, and
year — a rich source for RAG-based agricultural advisory systems.

Usage:
    from kcc_tool import KCCClient
    client = KCCClient(api_key="<your-key>")

    records  = client.get_by_state("Punjab", year="2024", month="6")
    summary  = client.monthly_summary("Maharashtra", "2024", "7")
    searches = client.search_queries("pest control wheat", state="Punjab")
"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Public sample key — max 10 records per call.
# Register at https://data.gov.in to get an unlimited key.
_SAMPLE_API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"

_BASE_URL = "https://api.data.gov.in/resource/cef25fe2-9231-4128-8aec-2c948fedd43f"


class KCCClient:
    """
    Query Kisan Call Centre transcripts from the data.gov.in portal.

    Each record is a single farmer call transcript containing:
        StateName, year, month — location/time context
        QueryText / KccAns     — farmer question and expert answer (field names
                                  vary by dataset revision; inspect sample records)

    The dataset is large (221k+ downloads, regularly updated) and is an excellent
    source for fine-tuning or RAG over real Indian agricultural queries.
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
        state:  Optional[str] = None,
        year:   Optional[str] = None,
        month:  Optional[str] = None,
        offset: int = 0,
        limit:  int = 10,
        fmt:    str = "json",
    ) -> Dict[str, Any]:
        """
        Fetch KCC transcript records with optional filters.

        Args:
            state  : State name, e.g. "Punjab" (field: StateName)
            year   : 4-digit year string, e.g. "2024"
            month  : Month number string, e.g. "6" or "06"
            offset : Records to skip (pagination)
            limit  : Records to return (max 10 for sample key)
            fmt    : "json" (default), "xml", or "csv"

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
            params["filters[StateName]"] = state
        if year:
            params["filters[year]"] = year
        if month:
            params["filters[month]"] = month

        try:
            resp = self._session.get(_BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            logger.error("KCC API HTTP %s: %s", e.response.status_code, e.response.text[:200])
            return {"error": str(e), "status_code": e.response.status_code}
        except requests.RequestException as e:
            logger.error("KCC API request failed: %s", e)
            return {"error": str(e)}
        except ValueError as e:
            logger.error("KCC API JSON parse error: %s", e)
            return {"error": f"JSON parse error: {e}"}

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def get_by_state(
        self,
        state: str,
        year:  Optional[str] = None,
        month: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Return KCC transcripts for a specific state.

        Args:
            state : e.g. "Punjab"
            year  : optional 4-digit year filter
            month : optional month number filter
            limit : max records (default 10)

        Returns:
            List of transcript dicts, empty list on error.
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
        Aggregate KCC call metadata for a state in a given month.

        Returns a summary dict with:
            state, year, month, total_records, records_fetched, field_names

        Note: With the sample API key, at most 10 records are returned.
        Use a registered key for full coverage.
        """
        resp    = self.get_data(state=state, year=year, month=month, limit=limit)
        records = resp.get("records", [])
        total   = resp.get("total", len(records))

        field_names = list(records[0].keys()) if records else []

        return {
            "state":           state,
            "year":            year,
            "month":           month,
            "total_records":   total,
            "records_fetched": len(records),
            "field_names":     field_names,
            "note": (
                "Sample key limited to 10 records per call. "
                "Register at data.gov.in for full dataset access."
            ) if self.api_key == _SAMPLE_API_KEY else None,
        }

    def search_queries(
        self,
        keyword: str,
        state:   Optional[str] = None,
        year:    Optional[str] = None,
        month:   Optional[str] = None,
        limit:   int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Client-side keyword filter over fetched KCC records.

        Fetches up to `limit` records (optionally filtered by state/year/month)
        and returns only those where any field value contains the keyword
        (case-insensitive).

        This is a best-effort search within a single API page.  For full-corpus
        search, use a registered key and paginate with get_data().

        Args:
            keyword : Search term, e.g. "pest control", "wheat", "irrigation"
            state   : Optional state filter
            year    : Optional year filter
            month   : Optional month filter
            limit   : Page size to fetch (default 10)

        Returns:
            Filtered list of transcript dicts.
        """
        records = self.get_data(state=state, year=year, month=month, limit=limit).get("records", [])
        kw = keyword.lower()
        return [
            r for r in records
            if any(kw in str(v).lower() for v in r.values())
        ]

    def count(
        self,
        state: Optional[str] = None,
        year:  Optional[str] = None,
        month: Optional[str] = None,
    ) -> int:
        """
        Return total matching records from API metadata (limit=1 to minimise transfer).
        """
        resp = self.get_data(state=state, year=year, month=month, limit=1)
        return int(resp.get("total", 0))

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def dump_json(self, data: Any) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# LangChain Tool Wrappers (uncomment when backend is ready)
# ---------------------------------------------------------------------------
# from langchain.tools import Tool
#
# def kcc_langchain_tools(api_key: str = _SAMPLE_API_KEY) -> list:
#     client = KCCClient(api_key=api_key)
#     return [
#         Tool(
#             name="KCC_GetByState",
#             func=lambda q: client.dump_json(
#                 # q format: "State|Year|Month"
#                 client.get_by_state(*[p.strip() for p in q.split("|")])
#             ),
#             description=(
#                 "Fetch Kisan Call Centre (KCC) farmer query transcripts for a state. "
#                 "Use this to find real farmer questions and expert answers as context "
#                 "for agricultural advisory responses. "
#                 "Input: pipe-separated string 'State|Year|Month', "
#                 "e.g. 'Punjab|2024|6'. Year and Month are optional."
#             ),
#         ),
#         Tool(
#             name="KCC_SearchQueries",
#             func=lambda q: client.dump_json(
#                 # q format: "keyword|State|Year|Month"  (State/Year/Month optional)
#                 (lambda parts: client.search_queries(
#                     parts[0],
#                     state=parts[1] if len(parts) > 1 else None,
#                     year=parts[2]  if len(parts) > 2 else None,
#                     month=parts[3] if len(parts) > 3 else None,
#                 ))([p.strip() for p in q.split("|")])
#             ),
#             description=(
#                 "Search Kisan Call Centre transcripts by keyword. Returns farmer questions "
#                 "and expert answers matching the keyword. Use for RAG context retrieval. "
#                 "Input: pipe-separated 'keyword|State|Year|Month' — State/Year/Month optional, "
#                 "e.g. 'wheat rust|Punjab' or 'irrigation schedule'."
#             ),
#         ),
#         Tool(
#             name="KCC_MonthlySummary",
#             func=lambda q: client.dump_json(
#                 # q format: "State|Year|Month"
#                 client.monthly_summary(*[p.strip() for p in q.split("|")])
#             ),
#             description=(
#                 "Get a summary (total call count, field names) of KCC data "
#                 "for a state in a given month. "
#                 "Input: pipe-separated string 'State|Year|Month', e.g. 'Maharashtra|2024|7'."
#             ),
#         ),
#     ]


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    client = KCCClient()

    print("=" * 60)
    print("Kisan Call Centre (KCC) Tool — Self Test")
    print("(Using sample API key — max 10 records per call)")
    print("=" * 60)

    # Test 1: Raw fetch (no filters)
    print("\n[1] Raw fetch (no filters, limit=3)")
    resp    = client.get_data(limit=3)
    records = resp.get("records", [])
    total   = resp.get("total", "?")
    print(f"    Total records in dataset : {total}")
    print(f"    Records returned         : {len(records)}")
    if records:
        sample = records[0]
        print(f"    Field names              : {list(sample.keys())}")
        print(f"    Sample record            :")
        for k, v in sample.items():
            snippet = str(v)[:120] + ("..." if len(str(v)) > 120 else "")
            print(f"      {k}: {snippet}")

    # Test 2: Filter by state
    print("\n[2] Filter by StateName='Punjab', limit=3")
    rows = client.get_by_state("Punjab", limit=3)
    print(f"    Records returned : {len(rows)}")
    for r in rows:
        keys = list(r.keys())
        print(f"    {keys[0]}: {r[keys[0]]}  |  fields: {keys}")

    # Test 3: Filter by state + month
    print("\n[3] Filter by StateName='Maharashtra', month='6', limit=3")
    rows = client.get_by_state("Maharashtra", month="6", limit=3)
    print(f"    Records returned : {len(rows)}")

    # Test 4: Monthly summary
    print("\n[4] Monthly summary — Punjab / year=2024 / month=6")
    summary = client.monthly_summary("Punjab", "2024", "6")
    print(client.dump_json(summary))

    # Test 5: search_queries
    print("\n[5] Search keyword='wheat' in Punjab")
    hits = client.search_queries("wheat", state="Punjab", limit=10)
    print(f"    Matching records : {len(hits)}")
    for r in hits[:2]:
        print(f"    {r}")

    # Test 6: count()
    print("\n[6] Total record count (all data)")
    n = client.count()
    print(f"    Total records in dataset: {n}")

    print("\nSelf-test complete.")
