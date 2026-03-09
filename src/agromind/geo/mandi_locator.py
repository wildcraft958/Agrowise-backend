"""Mandi locator — maps state/district to Agmark mandis and APMC mandis.

Two CSVs:
    Agmark Mandis: Mandi Name - Agmark, Mandi Name (Hi), District ID,
                   District Name - Agmark, State Name
    APMC Map:      Mandi ID, Mandi Code, Mandi Name, Mandi Name (Hi),
                   District ID, District Name, State ID, State Name
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

_Record = dict[str, Any]


class MandiLocator:
    """Locates Agmark mandis and APMC mandis by state or district ID."""

    def __init__(self, mandis_csv: str, apmc_csv: str) -> None:
        self._agmark: list[_Record] = []
        self._apmc: list[_Record] = []
        self._load_agmark(mandis_csv)
        self._load_apmc(apmc_csv)

    def _load_agmark(self, csv_path: str) -> None:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Agmark mandis CSV not found: {csv_path}")
        with open(path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                self._agmark.append({
                    "mandi_name": row["Mandi Name - Agmark"].strip(),
                    "mandi_name_hi": row["Mandi Name (Hi)"].strip(),
                    "district_id": row["District ID"].strip(),
                    "district_name": row["District Name - Agmark"].strip(),
                    "state_name": row["State Name"].strip(),
                })

    def _load_apmc(self, csv_path: str) -> None:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"APMC map CSV not found: {csv_path}")
        with open(path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                self._apmc.append({
                    "mandi_id": row["Mandi ID"].strip(),
                    "mandi_code": row["Mandi Code"].strip(),
                    "mandi_name": row["Mandi Name"].strip(),
                    "mandi_name_hi": row["Mandi Name (Hi)"].strip(),
                    "district_id": row["District ID"].strip(),
                    "district_name": row["District Name"].strip(),
                    "state_id": row["State ID"].strip(),
                    "state_name": row["State Name"].strip(),
                })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_mandis(self) -> int:
        return len(self._agmark) + len(self._apmc)

    def get_mandis_by_state(self, state: str) -> list[_Record]:
        """Return Agmark mandis for a state (case-insensitive)."""
        sl = state.strip().lower()
        return [m for m in self._agmark if m["state_name"].lower() == sl]

    def get_mandis_by_district_id(self, district_id: str) -> list[_Record]:
        """Return Agmark mandis for a district ID."""
        return [m for m in self._agmark if m["district_id"] == district_id]

    def get_apmc_mandis_by_state(self, state: str) -> list[_Record]:
        """Return APMC mandis for a state (case-insensitive)."""
        sl = state.strip().lower()
        return [m for m in self._apmc if m["state_name"].lower() == sl]

    def get_apmc_mandis_by_district_id(self, district_id: str) -> list[_Record]:
        """Return APMC mandis for a district ID."""
        return [m for m in self._apmc if m["district_id"] == district_id]
