"""
CIBRC Chemical Safety Tool
===========================
Loads cibrc_database.csv and checks agricultural chemicals against
the Indian CIBRC (Central Insecticides Board & Registration Committee) registry.

All regulatory data lives in the CSV — this file contains only loading and query logic.

Usage:
    from cibrc_tool import CIBRCClient
    client = CIBRCClient()
    print(client.check_chemical_safety("DDT"))
    print(client.check_batch(["Azoxystrobin", "Aldrin", "Acephate"]))
"""

import csv
import json
import difflib
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CIBRCClient:
    """
    Query the CIBRC database for chemical regulatory status in India.

    Statuses in the database:
        BANNED        — banned from manufacture, import, sale, and use
        REFUSED       — registration refused by CIBRC
        WITHDRAWN     — registration withdrawn
        RESTRICTED    — permitted with specific crop/use conditions
        PROPOSED_BAN  — currently registered but proposed for ban (2020 govt. proposal)
        REGISTERED    — cleared for use in India
    """

    # Common name aliases not in the CSV
    _ALIASES = {
        "ddt":       "dichloro-diphenyl-trichloroethane (ddt)",
        "neem oil":  "azadirachtin (neem products)",
        "neem":      "azadirachtin (neem products)",
        "gramoxone": "paraquat dimethyl sulfate (gramoxone)",
        "dbcp":      "dibromochloropropane",
    }

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cibrc_database.csv")
        self.db_path = db_path
        self.chemicals: Dict[str, Dict[str, Any]] = self._load()
        self.chemical_names: List[str] = sorted(self.chemicals.keys())

    def _load(self) -> Dict[str, Dict[str, Any]]:
        db: Dict[str, Dict[str, Any]] = {}
        try:
            with open(self.db_path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    key = row["chemical_name"].lower().strip()
                    db[key] = {
                        "chemical_name":        row["chemical_name"].strip(),
                        "status":               row["status"].strip(),
                        "restriction_details":  row["restriction_details"].strip(),
                        "registered_formulations": [
                            p.strip() for p in row["registered_formulations"].split("|") if p.strip()
                        ],
                    }
        except FileNotFoundError:
            logger.error("CIBRC database not found: %s", self.db_path)
            return {}

        # Resolve aliases to existing DB entries
        for alias, target_key in self._ALIASES.items():
            resolved = db.get(target_key) or next(
                (v for k, v in db.items() if target_key in k), None
            )
            if resolved:
                db[alias] = resolved

        logger.info("CIBRC loaded: %d entries from %s", len(db), self.db_path)
        return db

    # -------------------------------------------------------------------------

    def check_chemical_safety(self, query: str, threshold: float = 0.6) -> Dict[str, Any]:
        """
        Check a chemical name against the CIBRC database.

        Args:
            query:     Chemical name, e.g. "DDT", "Azoxystrobin", "Neem Oil"
            threshold: Fuzzy match cutoff 0–1 (default 0.6)

        Returns dict with keys:
            query, matched_chemical, match_score, status,
            is_safe_to_recommend, advisory,
            restriction_details (if RESTRICTED/PROPOSED_BAN),
            formulations_available (if any)
        """
        q = query.lower().strip()

        if q in self.chemicals:
            key, score = q, 1.0
        else:
            hits = difflib.get_close_matches(q, self.chemical_names, n=1, cutoff=threshold)
            if not hits:
                return {
                    "query": query,
                    "matched_chemical": None,
                    "match_score": 0.0,
                    "status": "UNKNOWN",
                    "is_safe_to_recommend": False,
                    "advisory": (
                        f"'{query}' was not found in the CIBRC database. "
                        "Cannot be verified as legally registered for use in India. "
                        "Do not recommend until confirmed with CIBRC."
                    ),
                }
            key = hits[0]
            score = round(difflib.SequenceMatcher(None, q, key).ratio(), 3)

        chem   = self.chemicals[key]
        status = chem["status"]
        name   = chem["chemical_name"]
        safe   = status == "REGISTERED"

        result: Dict[str, Any] = {
            "query":               query,
            "matched_chemical":    name,
            "match_score":         score,
            "status":              status,
            "is_safe_to_recommend": safe,
        }

        if status == "BANNED":
            result["advisory"] = (
                f"CRITICAL: {name} is BANNED in India — banned from manufacture, "
                "import, sale, and use. Do not recommend."
            )
        elif status == "REFUSED":
            result["advisory"] = (
                f"CRITICAL: {name} registration has been REFUSED by CIBRC. "
                "It cannot be legally sold or applied in India."
            )
        elif status == "WITHDRAWN":
            result["advisory"] = (
                f"WARNING: {name} registration has been WITHDRAWN. "
                "It is no longer legal to sell or recommend."
            )
        elif status == "RESTRICTED":
            details = chem["restriction_details"] or "Refer to CIBRC guidelines."
            result["advisory"] = (
                f"CAUTION: {name} is RESTRICTED in India. {details}"
            )
            result["restriction_details"] = details
            if chem["registered_formulations"]:
                result["formulations_available"] = chem["registered_formulations"]
        elif status == "PROPOSED_BAN":
            reason = chem["restriction_details"] or "Proposed for ban by Indian Govt. (May 2020)."
            result["advisory"] = (
                f"CAUTION: {name} is registered but PROPOSED FOR BAN (May 2020). "
                f"Reason: {reason} Recommend safer alternatives where possible."
            )
            result["restriction_details"] = reason
            if chem["registered_formulations"]:
                forms = chem["registered_formulations"]
                result["formulations_available"] = (
                    forms[:5] + [f"...and {len(forms) - 5} others"] if len(forms) > 5 else forms
                )
        elif status == "REGISTERED":
            result["advisory"] = f"APPROVED: {name} is registered for use in India by CIBRC."
            if chem["registered_formulations"]:
                forms = chem["registered_formulations"]
                result["formulations_available"] = (
                    forms[:5] + [f"...and {len(forms) - 5} others"] if len(forms) > 5 else forms
                )

        return result

    def check_batch(self, names: List[str], threshold: float = 0.6) -> Dict[str, Any]:
        """
        Check multiple chemicals at once.

        Returns:
            {
              "summary": {"safe_to_recommend": [...], "do_not_recommend": [...], "not_found": [...]},
              "results": {<name>: <check_chemical_safety result>, ...}
            }
        """
        results, safe, unsafe, unknown = {}, [], [], []
        for name in names:
            r = self.check_chemical_safety(name, threshold)
            results[name] = r
            if r["status"] == "UNKNOWN":
                unknown.append(name)
            elif r["is_safe_to_recommend"]:
                safe.append(name)
            else:
                unsafe.append(name)
        return {
            "summary": {
                "safe_to_recommend": safe,
                "do_not_recommend":  unsafe,
                "not_found":         unknown,
            },
            "results": results,
        }

    def list_banned(self) -> List[str]:
        """Sorted list of all BANNED chemical names."""
        return sorted(v["chemical_name"] for v in self.chemicals.values() if v["status"] == "BANNED")

    def list_restricted(self) -> List[Dict[str, Any]]:
        """All RESTRICTED chemicals with their specific conditions."""
        return sorted(
            [{"chemical_name": v["chemical_name"], "restriction_details": v["restriction_details"],
              "formulations": v["registered_formulations"]}
             for v in self.chemicals.values() if v["status"] == "RESTRICTED"],
            key=lambda x: x["chemical_name"],
        )

    def list_proposed_ban(self) -> List[Dict[str, str]]:
        """All chemicals proposed for ban (2020) with health concern notes."""
        return sorted(
            [{"chemical_name": v["chemical_name"], "reason": v["restriction_details"]}
             for v in self.chemicals.values() if v["status"] == "PROPOSED_BAN"],
            key=lambda x: x["chemical_name"],
        )

    def stats(self) -> Dict[str, int]:
        """Row counts by status."""
        counts: Dict[str, int] = {}
        for v in self.chemicals.values():
            counts[v["status"]] = counts.get(v["status"], 0) + 1
        return dict(sorted(counts.items()))

    def dump_json(self, data: Any) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# LangChain Tool Wrappers (uncomment when backend is ready)
# ---------------------------------------------------------------------------
# from langchain.tools import Tool
#
# def cibrc_langchain_tools() -> list:
#     client = CIBRCClient()
#     return [
#         Tool(
#             name="CIBRC_Check_Chemical",
#             func=lambda name: client.dump_json(client.check_chemical_safety(name)),
#             description=(
#                 "Check if an agricultural chemical is banned, restricted, or registered "
#                 "for use in India. ALWAYS call before recommending any pesticide or fungicide. "
#                 "Input: chemical name string, e.g. 'Chlorpyrifos'"
#             ),
#         ),
#         Tool(
#             name="CIBRC_Check_Batch",
#             func=lambda q: client.dump_json(client.check_batch([n.strip() for n in q.split(",")])),
#             description=(
#                 "Check multiple chemicals at once. "
#                 "Input: comma-separated names, e.g. 'Mancozeb, Aldrin, Neem Oil'"
#             ),
#         ),
#         Tool(
#             name="CIBRC_List_Banned",
#             func=lambda _: client.dump_json(client.list_banned()),
#             description="Returns the complete list of all chemicals BANNED in India.",
#         ),
#         Tool(
#             name="CIBRC_List_Restricted",
#             func=lambda _: client.dump_json(client.list_restricted()),
#             description="Returns all RESTRICTED chemicals with their specific crop/use conditions.",
#         ),
#     ]


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    client = CIBRCClient()

    print("Stats:", client.stats())
    print()

    tests = [
        ("DDT",            "RESTRICTED"),
        ("Aldrin",         "BANNED"),
        ("Toxaphene",      "BANNED"),
        ("Azoxystrobin",   "REGISTERED"),
        ("Neem Oil",       "REGISTERED"),
        ("Acephate",       "PROPOSED_BAN"),
        ("Carbendazim",    "PROPOSED_BAN"),
        ("Chlorpyrifos",   "RESTRICTED"),
        ("Monocrotophos",  "RESTRICTED"),
        ("FakeChemical",   "UNKNOWN"),
    ]

    passed = 0
    for name, expected in tests:
        r = client.check_chemical_safety(name)
        ok = r["status"] == expected
        passed += ok
        print(f"{'✓' if ok else '✗'} {name:20s} → {r['status']:15s} | {r['advisory'][:80]}...")

    print(f"\n{passed}/{len(tests)} passed")
    print(f"\nBanned: {len(client.list_banned())} | Restricted: {len(client.list_restricted())} | Proposed ban: {len(client.list_proposed_ban())}")
