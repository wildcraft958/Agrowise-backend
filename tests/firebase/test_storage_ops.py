"""Tests for StorageOps — firebase/storage_ops.py."""

from unittest.mock import MagicMock, patch

import pytest

from agromind.firebase.storage_ops import StorageOps


@pytest.fixture
def mock_bucket():
    return MagicMock()


@pytest.fixture
def ops(mock_bucket):
    return StorageOps(bucket=mock_bucket, max_upload_mb=5)


class TestStorageOpsInit:
    def test_instantiates(self, mock_bucket):
        s = StorageOps(bucket=mock_bucket)
        assert s is not None


class TestUploadBytes:
    def test_returns_blob_path(self, ops, mock_bucket):
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        result = ops.upload_bytes(
            data=b"fake image data",
            destination="diagnoses/user1/img.jpg",
            content_type="image/jpeg",
        )
        assert isinstance(result, str)
        assert "diagnoses/user1/img.jpg" in result

    def test_calls_upload_from_string(self, ops, mock_bucket):
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        ops.upload_bytes(b"data", "path/file.jpg", "image/jpeg")
        mock_blob.upload_from_string.assert_called_once_with(b"data", content_type="image/jpeg")

    def test_rejects_oversized_upload(self, ops):
        big_data = b"x" * (6 * 1024 * 1024)  # 6 MB > 5 MB limit
        with pytest.raises(ValueError, match="exceeds"):
            ops.upload_bytes(big_data, "path/file.jpg", "image/jpeg")


class TestSignedUrl:
    def test_returns_url_string(self, ops, mock_bucket):
        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/signed"
        mock_bucket.blob.return_value = mock_blob
        url = ops.signed_url("diagnoses/user1/img.jpg", expiry_minutes=60)
        assert isinstance(url, str)
        assert url.startswith("https://")


class TestDelete:
    def test_calls_blob_delete(self, ops, mock_bucket):
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        ops.delete("diagnoses/user1/img.jpg")
        mock_blob.delete.assert_called_once()
