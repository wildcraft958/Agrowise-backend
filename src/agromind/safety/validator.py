"""CIBRC chemical safety post-filter.

Scans LLM output text for banned chemicals. In strict mode, marks the response
as unsafe (caller should replace or reject it). In lenient mode, marks unsafe
but allows the caller to warn rather than reject.

Matching is whole-word, case-insensitive using regex word boundaries so that
"Aldrington" does not match "Aldrin".
"""

from __future__ import annotations

import re


class SafetyValidator:
    """Scans text for banned agricultural chemicals."""

    def __init__(
        self,
        banned_chemicals: set[str],
        strict_mode: bool = True,
    ) -> None:
        self._strict = strict_mode
        # Pre-compile one pattern per chemical for whole-word matching
        self._patterns: dict[str, re.Pattern[str]] = {
            chem: re.compile(rf"\b{re.escape(chem)}\b", re.IGNORECASE)
            for chem in banned_chemicals
        }

    def scan(self, text: str) -> list[str]:
        """Return list of banned chemical names found in text (canonical casing)."""
        found: list[str] = []
        for chem, pattern in self._patterns.items():
            if pattern.search(text):
                found.append(chem)
        return found

    def validate(self, text: str) -> dict:
        """Validate text against the banned chemical list.

        Returns:
            Dict with keys:
                safe (bool): True if no banned chemicals found.
                violations (list[str]): Banned chemicals found.
                strict (bool): Whether strict mode is on.
        """
        violations = self.scan(text)
        return {
            "safe": len(violations) == 0,
            "violations": violations,
            "strict": self._strict,
        }
