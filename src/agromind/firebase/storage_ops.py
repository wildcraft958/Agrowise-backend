"""Cloud Storage operations for AgroMind.

Handles upload of diagnosis images, voice audio, and user avatars.
Max upload size is configurable (default 5 MB from config.yaml).
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)


class StorageOps:
    """Thin wrapper around firebase_admin.storage bucket operations."""

    def __init__(self, bucket: Any, max_upload_mb: int = 5) -> None:
        self._bucket = bucket
        self._max_bytes = max_upload_mb * 1024 * 1024

    def upload_bytes(
        self,
        data: bytes,
        destination: str,
        content_type: str,
    ) -> str:
        """Upload raw bytes to Cloud Storage.

        Args:
            data: File bytes to upload.
            destination: GCS blob path, e.g. "diagnoses/user1/img.jpg".
            content_type: MIME type, e.g. "image/jpeg".

        Returns:
            The destination path (blob name).

        Raises:
            ValueError: If data exceeds max_upload_mb.
        """
        if len(data) > self._max_bytes:
            max_mb = self._max_bytes // (1024 * 1024)
            raise ValueError(
                f"Upload of {len(data)} bytes exceeds {max_mb} MB limit"
            )
        blob = self._bucket.blob(destination)
        blob.upload_from_string(data, content_type=content_type)
        logger.info("Uploaded %d bytes to gs://%s", len(data), destination)
        return destination

    def signed_url(self, blob_path: str, expiry_minutes: int = 60) -> str:
        """Generate a signed download URL for a blob.

        Args:
            blob_path: GCS blob path.
            expiry_minutes: URL validity duration in minutes.

        Returns:
            Signed HTTPS URL string.
        """
        blob = self._bucket.blob(blob_path)
        expiry = datetime.timedelta(minutes=expiry_minutes)
        return blob.generate_signed_url(expiration=expiry, method="GET")

    def delete(self, blob_path: str) -> None:
        """Delete a blob from Cloud Storage."""
        blob = self._bucket.blob(blob_path)
        blob.delete()
        logger.info("Deleted gs://%s", blob_path)
