"""Tests for Firebase init — firebase/client.py."""

from unittest.mock import MagicMock, patch

import pytest

from agromind.firebase.client import get_firestore, get_storage_bucket, init_firebase


class TestInitFirebase:
    def test_returns_true_when_enabled(self):
        with patch("agromind.firebase.client.firebase_admin") as mock_admin:
            mock_admin.get_app.side_effect = ValueError("no app")
            mock_admin.initialize_app.return_value = MagicMock()
            result = init_firebase(storage_bucket="test-bucket", enabled=True)
        assert result is True

    def test_returns_false_when_disabled(self):
        result = init_firebase(enabled=False)
        assert result is False

    def test_skips_double_init(self):
        with patch("agromind.firebase.client.firebase_admin") as mock_admin:
            mock_admin.get_app.return_value = MagicMock()  # app already exists
            result = init_firebase(storage_bucket="test-bucket", enabled=True)
        assert result is True
        mock_admin.initialize_app.assert_not_called()

    def test_uses_application_default_credentials(self):
        with patch("agromind.firebase.client.firebase_admin") as mock_admin:
            with patch("agromind.firebase.client.credentials") as mock_creds:
                mock_admin.get_app.side_effect = ValueError("no app")
                mock_admin.initialize_app.return_value = MagicMock()
                init_firebase(storage_bucket="bucket", enabled=True)
        mock_creds.ApplicationDefault.assert_called_once()


class TestGetFirestore:
    def test_returns_client(self):
        with patch("agromind.firebase.client.firestore") as mock_fs:
            mock_fs.client.return_value = MagicMock()
            db = get_firestore()
        assert db is not None


class TestGetStorageBucket:
    def test_returns_bucket(self):
        with patch("agromind.firebase.client.storage") as mock_storage:
            mock_storage.bucket.return_value = MagicMock()
            bucket = get_storage_bucket()
        assert bucket is not None
