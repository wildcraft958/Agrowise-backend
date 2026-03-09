"""IMD Agromet station mapper — maps state/district to IMD advisory URLs.

CSV columns:
    State, District, State ID, District ID, IMD Code,
    Example (Regional) ..., Example (English) ...

IMD Code format: "<StateID>_<DistrictID>" e.g. "16_1603"

Advisory URL templates:
    Regional: .../District AAS Bulletin/Regional Bulletin/<IMD_CODE>_<DATE>_R.pdf
    English:  .../District AAS Bulletin/English Bulletin/<IMD_CODE>_<DATE>_E.pdf
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

_BASE_URL = "https://www.imdagrimet.gov.in/accessData.php?path=Files/District%20AAS%20Bulletin"
_REGIONAL_TEMPLATE = _BASE_URL + "/Regional%20Bulletin/{imd_code}_{date}_R.pdf"
_ENGLISH_TEMPLATE = _BASE_URL + "/English%20Bulletin/{imd_code}_{date}_E.pdf"

_Record = dict[str, Any]


class IMDStationMapper:
    """Maps state+district names to IMD codes and advisory PDF URLs."""

    def __init__(self, csv_path: str) -> None:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"IMD stations CSV not found: {csv_path}")

        # (state_lower, district_lower) → record
        self._index: dict[tuple[str, str], _Record] = {}

        with open(path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                state = row["State"].strip()
                district = row["District"].strip()
                imd_code = row["IMD Code"].strip()
                state_id = row["State ID"].strip()
                district_id = row["District ID"].strip()
                if not imd_code:
                    continue
                key = (state.lower(), district.lower())
                self._index[key] = {
                    "state": state,
                    "district": district,
                    "state_id": state_id,
                    "district_id": district_id,
                    "imd_code": imd_code,
                }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_stations(self) -> int:
        return len(self._index)

    def get_imd_code(self, state: str, district: str) -> str | None:
        """Return the IMD code string for a state+district, or None."""
        record = self._index.get((state.strip().lower(), district.strip().lower()))
        return record["imd_code"] if record else None

    def get_station(self, state: str, district: str) -> _Record | None:
        """Return the full station record for a state+district, or None."""
        return self._index.get((state.strip().lower(), district.strip().lower()))

    def get_advisory_url(
        self,
        state: str,
        district: str,
        date: str,
        lang: str = "english",
    ) -> str | None:
        """Return the IMD advisory PDF URL for a date (YYYY-MM-DD).

        Args:
            state: Indian state name.
            district: District name.
            date: Date string in YYYY-MM-DD format.
            lang: "english" (default) or "regional".

        Returns:
            URL string or None if district not found.
        """
        code = self.get_imd_code(state, district)
        if code is None:
            return None
        template = _REGIONAL_TEMPLATE if lang.lower() == "regional" else _ENGLISH_TEMPLATE
        return template.format(imd_code=code, date=date)
