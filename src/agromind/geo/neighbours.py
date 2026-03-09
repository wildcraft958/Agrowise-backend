"""District neighbour graph — adjacency lookup by name.

CSV has a comment row 1 that is skipped; row 2 is the header.

CSV columns:
    Main State Name, Main District Name,
    Neighbour - 1 … Neighbour - 7  (empty string when no more neighbours)

Neighbours are stored by district name only (no state for neighbours in the CSV).
`are_neighbours` checks bidirectionally.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

_NEIGHBOUR_COLS = [f"Neighbour - {i}" for i in range(1, 8)]


class NeighbourGraph:
    """In-memory district adjacency graph backed by the District Neighbour Map CSV."""

    def __init__(self, csv_path: str) -> None:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Neighbour map CSV not found: {csv_path}")

        # Row 0 is a comment ("Mapped by Name"), row 1 is the real header
        lines = path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
        data = "".join(lines[1:])  # skip comment row

        # (state_lower, district_lower) → list of neighbour district names (canonical)
        self._adjacency: dict[tuple[str, str], list[str]] = {}

        reader = csv.DictReader(io.StringIO(data))
        for row in reader:
            state = row["Main State Name"].strip()
            district = row["Main District Name"].strip()
            neighbours = [
                row[col].strip()
                for col in _NEIGHBOUR_COLS
                if row.get(col, "").strip()
            ]
            key = (state.lower(), district.lower())
            self._adjacency[key] = neighbours

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_districts(self) -> int:
        return len(self._adjacency)

    def get_neighbours(self, state: str, district: str) -> list[dict[str, str]]:
        """Return list of neighbour dicts with 'district_name' key."""
        key = (state.strip().lower(), district.strip().lower())
        names = self._adjacency.get(key, [])
        return [{"district_name": n} for n in names]

    def get_neighbour_names(self, state: str, district: str) -> list[str]:
        """Return list of neighbour district name strings."""
        key = (state.strip().lower(), district.strip().lower())
        return list(self._adjacency.get(key, []))

    def are_neighbours(
        self,
        state1: str,
        district1: str,
        state2: str,
        district2: str,
    ) -> bool:
        """Return True if district1 and district2 are adjacent (bidirectional check)."""
        d2_lower = district2.strip().lower()
        forward = [n.lower() for n in self.get_neighbour_names(state1, district1)]
        if d2_lower in forward:
            return True
        # Check reverse
        d1_lower = district1.strip().lower()
        reverse = [n.lower() for n in self.get_neighbour_names(state2, district2)]
        return d1_lower in reverse
