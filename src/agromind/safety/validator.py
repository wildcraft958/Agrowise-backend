"""CIBRC safety post-filter stub."""
from __future__ import annotations


class SafetyValidator:
    def __init__(self, banned_chemicals: set[str], strict_mode: bool = True) -> None:
        raise NotImplementedError

    def scan(self, text: str) -> list[str]:
        raise NotImplementedError

    def validate(self, text: str) -> dict:
        raise NotImplementedError
