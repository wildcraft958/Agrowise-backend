"""FCM push notification client.

Wraps firebase_admin.messaging for single and multicast push notifications.
When `enabled=False`, all methods return immediately with empty/zero results
so the rest of the pipeline is unaffected.
"""

from __future__ import annotations

import logging

from firebase_admin import messaging

logger = logging.getLogger(__name__)


class FCMClient:
    """Sends FCM push notifications via Firebase Admin SDK."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> str:
        """Send a push notification to a single device.

        Args:
            token: FCM device registration token.
            title: Notification title.
            body: Notification body text.
            data: Optional key-value data payload.

        Returns:
            FCM message ID string, or "" if disabled.
        """
        if not self._enabled:
            return ""

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
            data=data or {},
        )
        msg_id = messaging.send(message)
        logger.info("FCM sent: %s", msg_id)
        return msg_id

    def send_multicast(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> dict:
        """Send a push notification to multiple devices.

        Returns:
            Dict with success_count and failure_count.
        """
        if not self._enabled:
            return {"success_count": 0, "failure_count": 0}

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=tokens,
            data=data or {},
        )
        response = messaging.send_each_for_multicast(message)
        logger.info(
            "FCM multicast: %d success, %d failure",
            response.success_count,
            response.failure_count,
        )
        return {
            "success_count": response.success_count,
            "failure_count": response.failure_count,
        }
