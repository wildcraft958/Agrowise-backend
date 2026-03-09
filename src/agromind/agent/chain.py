"""Agent chain stub."""
from __future__ import annotations

from langchain_core.messages import BaseMessage


class AgroMindAgent:
    def __init__(self) -> None:
        raise NotImplementedError

    def invoke(self, user_message: str, context: dict | None = None) -> dict:
        raise NotImplementedError
