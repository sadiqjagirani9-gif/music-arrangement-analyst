import pytest


def test_api_health_shape():
    pytest.importorskip("fastapi")
    from backend.main import app
    assert app.title == "Music Arrangement Analyst"


def test_qq_auth_status_endpoint():
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from backend.main import app

    response = TestClient(app).get("/api/sources/qq/auth/status")
    assert response.status_code == 200
    assert response.json()["grants_music_entitlement"] is False
