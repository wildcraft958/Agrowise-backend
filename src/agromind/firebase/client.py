"""Firebase Admin SDK initializer.

Uses ApplicationDefault credentials (GOOGLE_APPLICATION_CREDENTIALS env var)
so the same service account handles Vertex AI + Firebase.

Set `firebase.enabled: false` in config.yaml to skip Firebase entirely
(useful for local testing without a service account JSON).
"""

from __future__ import annotations

import logging

import firebase_admin
from firebase_admin import credentials, firestore, storage

logger = logging.getLogger(__name__)

_initialized = False


def init_firebase(storage_bucket: str | None = None, enabled: bool = True) -> bool:
    """Initialize the Firebase Admin SDK.

    Safe to call multiple times — skips if already initialized.

    Args:
        storage_bucket: GCS bucket name, e.g. "agrowise-192e3.firebasestorage.app".
        enabled: If False, skips initialization (returns False immediately).

    Returns:
        True if Firebase is initialized (or was already), False if disabled.
    """
    if not enabled:
        logger.info("Firebase disabled — skipping init")
        return False

    try:
        firebase_admin.get_app()
        logger.debug("Firebase already initialized")
        return True
    except ValueError:
        pass  # App not yet initialized

    cred = credentials.ApplicationDefault()
    options = {}
    if storage_bucket:
        options["storageBucket"] = storage_bucket

    firebase_admin.initialize_app(cred, options)
    logger.info("Firebase Admin SDK initialized (bucket=%s)", storage_bucket)
    return True


def get_firestore():
    """Return a Firestore client."""
    return firestore.client()


def get_storage_bucket():
    """Return the default Cloud Storage bucket."""
    return storage.bucket()
