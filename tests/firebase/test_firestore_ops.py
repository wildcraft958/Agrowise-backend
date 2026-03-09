"""Tests for FirestoreOps — firebase/firestore_ops.py."""

from unittest.mock import MagicMock, call

import pytest

from agromind.firebase.firestore_ops import FirestoreOps


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def ops(mock_db):
    return FirestoreOps(db=mock_db)


class TestFirestoreOpsInit:
    def test_instantiates(self, mock_db):
        ops = FirestoreOps(db=mock_db)
        assert ops is not None


class TestSaveChatMessage:
    def test_returns_document_id(self, ops, mock_db):
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "msg_123"
        mock_db.collection.return_value.document.return_value.collection.return_value \
            .add.return_value = (None, mock_doc_ref)
        result = ops.save_chat_message(
            user_id="user_1",
            message={"role": "user", "text": "Hello"},
        )
        assert isinstance(result, str)

    def test_writes_to_correct_collection_path(self, ops, mock_db):
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "msg_1"
        mock_db.collection.return_value.document.return_value.collection.return_value \
            .add.return_value = (None, mock_doc_ref)
        ops.save_chat_message(user_id="user_abc", message={"role": "user", "text": "Hi"})
        mock_db.collection.assert_called_with("chats")


class TestGetChatHistory:
    def test_returns_list(self, ops, mock_db):
        mock_docs = [MagicMock(to_dict=lambda: {"role": "user", "text": "q"})]
        mock_db.collection.return_value.document.return_value.collection.return_value \
            .order_by.return_value.limit.return_value.stream.return_value = iter(mock_docs)
        result = ops.get_chat_history(user_id="user_1")
        assert isinstance(result, list)


class TestSaveDiagnosis:
    def test_returns_id(self, ops, mock_db):
        mock_ref = MagicMock()
        mock_ref.id = "diag_1"
        mock_db.collection.return_value.add.return_value = (None, mock_ref)
        result = ops.save_diagnosis({"userId": "u1", "disease": "rust", "confidence": 0.9})
        assert isinstance(result, str)


class TestCreateAlert:
    def test_returns_id(self, ops, mock_db):
        mock_ref = MagicMock()
        mock_ref.id = "alert_1"
        mock_db.collection.return_value.add.return_value = (None, mock_ref)
        result = ops.create_alert({"type": "weather", "severity": "high", "userId": "u1"})
        assert isinstance(result, str)


class TestGetUser:
    def test_returns_dict_when_exists(self, ops, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Ravi", "phone": "+919999999999"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        result = ops.get_user("user_1")
        assert result is not None
        assert result["name"] == "Ravi"

    def test_returns_none_when_not_exists(self, ops, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        result = ops.get_user("no_such_user")
        assert result is None


class TestUpsertUser:
    def test_calls_set_with_merge(self, ops, mock_db):
        ops.upsert_user("user_1", {"name": "Ravi"})
        mock_db.collection.return_value.document.return_value.set.assert_called_once()
