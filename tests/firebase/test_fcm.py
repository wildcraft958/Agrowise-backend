"""Tests for FCMClient — firebase/fcm.py."""

from unittest.mock import MagicMock, patch

import pytest

from agromind.firebase.fcm import FCMClient


@pytest.fixture
def client():
    return FCMClient(enabled=True)


@pytest.fixture
def disabled():
    return FCMClient(enabled=False)


class TestFCMClientInit:
    def test_instantiates_enabled(self):
        c = FCMClient(enabled=True)
        assert c is not None

    def test_instantiates_disabled(self):
        c = FCMClient(enabled=False)
        assert c is not None


class TestSend:
    def test_returns_message_id(self, client):
        with patch("agromind.firebase.fcm.messaging") as mock_msg:
            mock_msg.send.return_value = "projects/x/messages/123"
            result = client.send(
                token="device_token_abc",
                title="Weather Alert",
                body="Heavy rain expected tomorrow.",
            )
        assert isinstance(result, str)

    def test_disabled_returns_empty_string(self, disabled):
        result = disabled.send(token="tok", title="T", body="B")
        assert result == ""

    def test_passes_data_payload(self, client):
        with patch("agromind.firebase.fcm.messaging") as mock_msg:
            mock_msg.send.return_value = "msg_id"
            client.send(token="tok", title="T", body="B", data={"type": "alert"})
        # Verify messaging.Message was constructed with the data kwarg
        mock_msg.Message.assert_called_once()
        _, kwargs = mock_msg.Message.call_args
        assert kwargs.get("data") == {"type": "alert"}


class TestSendMulticast:
    def test_returns_dict_with_success_count(self, client):
        with patch("agromind.firebase.fcm.messaging") as mock_msg:
            mock_response = MagicMock()
            mock_response.success_count = 2
            mock_response.failure_count = 0
            mock_msg.send_each_for_multicast.return_value = mock_response
            result = client.send_multicast(
                tokens=["tok1", "tok2"],
                title="Alert",
                body="Pest warning",
            )
        assert isinstance(result, dict)
        assert "success_count" in result

    def test_disabled_returns_zero_counts(self, disabled):
        result = disabled.send_multicast(tokens=["t1", "t2"], title="T", body="B")
        assert result.get("success_count") == 0
