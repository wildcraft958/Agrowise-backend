"""Tests for GET /health — api/health.py."""

import pytest
from fastapi.testclient import TestClient

from agromind.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_returns_json(self, client):
        response = client.get("/health")
        assert response.headers["content-type"].startswith("application/json")

    def test_has_status_ok(self, client):
        response = client.get("/health")
        data = response.json()
        assert data.get("status") == "ok"

    def test_has_version_key(self, client):
        response = client.get("/health")
        data = response.json()
        assert "version" in data
