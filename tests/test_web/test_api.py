"""Tests for web API endpoints."""

from fastapi.testclient import TestClient

from phone_farm.web.app import app


def _client() -> TestClient:
    return TestClient(app)


def test_home_page_returns_html() -> None:
    response = _client().get("/")
    assert response.status_code == 200
    assert "Phone Farm" in response.text


def test_phones_page_returns_html() -> None:
    response = _client().get("/phones")
    assert response.status_code == 200
    assert "Phone" in response.text


def test_reports_page_returns_html() -> None:
    response = _client().get("/reports")
    assert response.status_code == 200
    assert "Reports" in response.text


def test_settings_page_returns_html() -> None:
    response = _client().get("/settings")
    assert response.status_code == 200
    assert "Settings" in response.text


def test_health_endpoint() -> None:
    response = _client().get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert isinstance(data["checks"], list)


def test_phones_list_endpoint() -> None:
    response = _client().get("/api/phones")
    assert response.status_code == 200
    data = response.json()
    assert "phones" in data
