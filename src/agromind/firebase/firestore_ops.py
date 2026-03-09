"""Firestore CRUD operations for AgroMind collections.

Collections used:
    chats/{userId}/messages/{messageId}
    diagnoses/{diagnosisId}
    alerts/{alertId}
    users/{userId}
"""

from __future__ import annotations

import logging
from typing import Any

from google.cloud.firestore_v1 import SERVER_TIMESTAMP

logger = logging.getLogger(__name__)


class FirestoreOps:
    """CRUD helpers for Firestore collections."""

    def __init__(self, db: Any) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Chat messages
    # ------------------------------------------------------------------

    def save_chat_message(self, user_id: str, message: dict) -> str:
        """Append a chat message to chats/{user_id}/messages.

        Returns the new document ID.
        """
        payload = {**message, "timestamp": SERVER_TIMESTAMP}
        _, ref = (
            self._db.collection("chats")
            .document(user_id)
            .collection("messages")
            .add(payload)
        )
        return ref.id

    def get_chat_history(self, user_id: str, limit: int = 20) -> list[dict]:
        """Return up to `limit` messages for a user ordered by timestamp."""
        docs = (
            self._db.collection("chats")
            .document(user_id)
            .collection("messages")
            .order_by("timestamp")
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    # ------------------------------------------------------------------
    # Diagnoses
    # ------------------------------------------------------------------

    def save_diagnosis(self, diagnosis: dict) -> str:
        """Save a diagnosis record to diagnoses collection. Returns doc ID."""
        payload = {**diagnosis, "timestamp": SERVER_TIMESTAMP}
        _, ref = self._db.collection("diagnoses").add(payload)
        return ref.id

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def create_alert(self, alert: dict) -> str:
        """Create an alert document. Returns doc ID."""
        payload = {**alert, "timestamp": SERVER_TIMESTAMP, "isRead": False}
        _, ref = self._db.collection("alerts").add(payload)
        return ref.id

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def get_user(self, user_id: str) -> dict | None:
        """Return user document dict or None if not found."""
        doc = self._db.collection("users").document(user_id).get()
        return doc.to_dict() if doc.exists else None

    def upsert_user(self, user_id: str, data: dict) -> None:
        """Create or update a user document (merge=True)."""
        self._db.collection("users").document(user_id).set(data, merge=True)
