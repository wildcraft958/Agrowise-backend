"""Crop name normalizer — maps raw Agmark crop names to clean canonical names.

CSV columns:
    Agmark Crop Name (Raw), Crop Name - Cleaned, Variety Name - Cleaned,
    Source, Crop Name (Hindi), Crop Name (Marathi), Variety Name (Hindi), Crop Type
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

_Record = dict[str, Any]


class CropNormalizer:
    """Normalizes raw Agmark crop name strings to canonical crop names."""

    def __init__(self, csv_path: str) -> None:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Agmark crops CSV not found: {csv_path}")

        # raw_lower → normalized record
        self._by_raw: dict[str, _Record] = {}
        # canonical_lower → canonical record (first seen wins)
        self._by_canonical: dict[str, _Record] = {}

        with open(path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                raw = row["Agmark Crop Name (Raw)"].strip()
                canonical = row["Crop Name - Cleaned"].strip()
                if not raw or not canonical:
                    continue
                record: _Record = {
                    "crop_name": canonical,
                    "variety_name": row["Variety Name - Cleaned"].strip() or None,
                    "crop_type": row["Crop Type"].strip() or None,
                    "crop_name_hi": row["Crop Name (Hindi)"].strip() or None,
                }
                self._by_raw[raw.lower()] = record
                # Canonical lookup (only if not already present)
                if canonical.lower() not in self._by_canonical:
                    self._by_canonical[canonical.lower()] = record

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_crops(self) -> int:
        return len(self._by_raw)

    def normalize(self, crop_name: str) -> _Record | None:
        """Return the normalized record for a raw or canonical crop name, or None."""
        key = crop_name.strip().lower()
        return self._by_raw.get(key) or self._by_canonical.get(key)

    def list_canonical_names(self) -> list[str]:
        """Return sorted list of unique canonical crop names."""
        return sorted({r["crop_name"] for r in self._by_raw.values()})
