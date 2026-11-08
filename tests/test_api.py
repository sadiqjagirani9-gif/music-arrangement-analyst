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


def test_capture_device_and_start_endpoints(monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from backend import main

    class FakeCaptureManager:
        def list_devices(self):
            return [{"id": "fake:loop", "name": "Loopback", "backend": "fake", "kind": "output_loopback", "is_loopback": True, "is_default": True, "max_channels": 2}]

        def start(self, config):
            return {"id": "session-1", "state": "starting", "sample_rate": config.sample_rate, "device": self.list_devices()[0]}

    monkeypatch.setattr(main, "capture_manager", FakeCaptureManager())
    client = TestClient(main.app)
    devices = client.get("/api/capture/devices")
    assert devices.status_code == 200
    assert devices.json()["devices"][0]["is_loopback"] is True
    started = client.post("/api/capture/sessions", json={"device_id": "fake:loop", "sample_rate": 44100})
    assert started.status_code == 200
    assert started.json()["sample_rate"] == 44100
