"""Location resolver — normalizes partial location input to state/district/block IDs.

Loads `Location hierarchy.csv` once at startup and provides fast lookups by name.
All comparisons are case-insensitive. No fuzzy matching (returns None on mismatch).

CSV columns:
    State ID, State Name, State Name (Hindi),
    Division ID, Division Name, Division Name (Hindi),
    District Name, District ID, District Name (Hindi),
    Block ID, Block Name, Block Name (Hindi),
    Present in IMD Agromet
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

_Record = dict[str, Any]


class LocationResolver:
    """In-memory location hierarchy resolver backed by the Location hierarchy CSV."""

    def __init__(self, csv_path: str) -> None:
        self._records: list[_Record] = []
        self._load(csv_path)
        self._build_index()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self, csv_path: str) -> None:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Location hierarchy CSV not found: {csv_path}")

        with open(path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                self._records.append({
                    "state_id": row["State ID"].strip(),
                    "state_name": row["State Name"].strip(),
                    "district_id": row["District ID"].strip(),
                    "district_name": row["District Name"].strip(),
                    "block_id": int(row["Block ID"].strip()),
                    "block_name": row["Block Name"].strip(),
                    "in_imd_agromet": row["Present in IMD Agromet"].strip().upper() == "TRUE",
                })

    def _build_index(self) -> None:
        # block_id → record (unique)
        self._by_block_id: dict[int, _Record] = {r["block_id"]: r for r in self._records}

        # (state_lower, district_lower, block_lower) → record
        self._by_sdb: dict[tuple[str, str, str], _Record] = {
            (r["state_name"].lower(), r["district_name"].lower(), r["block_name"].lower()): r
            for r in self._records
        }

        # state_lower → sorted list of unique district names
        states_map: dict[str, set[str]] = {}
        districts_map: dict[tuple[str, str], set[str]] = {}
        for r in self._records:
            sl = r["state_name"].lower()
            dl = r["district_name"].lower()
            states_map.setdefault(sl, set()).add(r["state_name"])
            districts_map.setdefault((sl, dl), set()).add(r["district_name"])

        self._canonical_state: dict[str, str] = {k: next(iter(v)) for k, v in states_map.items()}
        self._canonical_district: dict[tuple[str, str], str] = {
            k: next(iter(v)) for k, v in districts_map.items()
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_blocks(self) -> int:
        return len(self._records)

    def resolve(
        self,
        state: str,
        district: str,
        block: str,
    ) -> _Record | None:
        """Return the full record for a state/district/block triplet, or None."""
        key = (state.strip().lower(), district.strip().lower(), block.strip().lower())
        return self._by_sdb.get(key)

    def resolve_state(self, state: str) -> list[_Record]:
        """Return all records for a state."""
        sl = state.strip().lower()
        return [r for r in self._records if r["state_name"].lower() == sl]

    def resolve_district(self, state: str, district: str) -> list[_Record]:
        """Return all blocks for a state+district."""
        sl = state.strip().lower()
        dl = district.strip().lower()
        return [
            r for r in self._records
            if r["state_name"].lower() == sl and r["district_name"].lower() == dl
        ]

    def get_by_block_id(self, block_id: int) -> _Record | None:
        """Return the record for a numeric block ID."""
        return self._by_block_id.get(block_id)

    def list_states(self) -> list[str]:
        """Return sorted list of canonical state names."""
        return sorted({r["state_name"] for r in self._records})

    def list_districts(self, state: str) -> list[str]:
        """Return sorted list of canonical district names for a state."""
        sl = state.strip().lower()
        return sorted({
            r["district_name"] for r in self._records if r["state_name"].lower() == sl
        })

    def list_blocks(self, state: str, district: str) -> list[str]:
        """Return sorted list of block names for a state+district."""
        sl = state.strip().lower()
        dl = district.strip().lower()
        return sorted({
            r["block_name"]
            for r in self._records
            if r["state_name"].lower() == sl and r["district_name"].lower() == dl
        })
