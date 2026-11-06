import pytest


def test_api_health_shape():
    pytest.importorskip("fastapi")
    from backend.main import app
    assert app.title == "Music Arrangement Analyst"
