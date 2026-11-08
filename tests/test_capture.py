from __future__ import annotations

import time
import wave
from contextlib import contextmanager

import numpy as np

from backend.capture.manager import CaptureManager
from backend.capture.models import CaptureConfig, CaptureDevice
from backend.capture.validation import validate_wav


class FakeAudioBackend:
    def __init__(self, silent=False):
        self.silent = silent
        self.phase = 0

    def list_devices(self):
        return [CaptureDevice("fake:loopback", "Test Loopback", "fake", "output_loopback", True, True)]

    @contextmanager
    def open_stream(self, device_id, sample_rate, channels, blocksize):
        def read(frames):
            time.sleep(0.004)
            if self.silent:
                return np.zeros((frames, channels), dtype=np.float32)
            indexes = np.arange(frames) + self.phase
            self.phase += frames
            tone = 0.2 * np.sin(2 * np.pi * 440 * indexes / sample_rate)
            return np.repeat(tone[:, None], channels, axis=1).astype(np.float32)
        yield read


def wait_for(session, states, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if session.state in states:
            return
        time.sleep(0.01)
    raise AssertionError(f"session remained in {session.state}")


def test_capture_pause_resume_save_validate_and_analyze(tmp_path):
    analyzed = []
    manager = CaptureManager(tmp_path, lambda path, metadata: analyzed.append((path, metadata)) or {"id": "analysis-1"}, FakeAudioBackend())
    started = manager.start(CaptureConfig("fake:loopback", 48000, 2))
    session = manager.get(started["id"])
    wait_for(session, {"recording"})
    manager.pause(session.id)
    assert session.state == "paused"
    manager.resume(session.id)
    wait_for(session, {"recording"})
    while session.frames_written < 26000:
        time.sleep(0.01)
    manager.stop(session.id)
    wait_for(session, {"completed"})
    status = session.to_dict()
    assert status["validation"]["valid"] is True
    assert status["analysis_id"] == "analysis-1"
    assert status["file_size_bytes"] > 44
    assert status["waveform"]
    assert analyzed[0][1]["platform"] == "live_capture"
    with wave.open(str(session.output_path), "rb") as wav:
        assert wav.getframerate() == 48000
        assert wav.getsampwidth() == 2


def test_silent_capture_is_rejected(tmp_path):
    manager = CaptureManager(tmp_path, lambda path, metadata: {"id": "should-not-run"}, FakeAudioBackend(silent=True))
    started = manager.start(CaptureConfig("fake:loopback", 44100, 2, max_duration_seconds=1))
    session = manager.get(started["id"])
    wait_for(session, {"invalid"})
    assert session.analysis_id is None
    assert "静音" in (session.error or "")


def test_validation_detects_incomplete_wav(tmp_path):
    path = tmp_path / "empty.wav"
    path.write_bytes(b"RIFF")
    result = validate_wav(path)
    assert result.valid is False
    assert result.issues


def test_capture_config_rejects_unsupported_rate():
    config = CaptureConfig("fake:loopback", 96000)
    try:
        config.validate()
    except ValueError as exc:
        assert "44100" in str(exc)
    else:
        raise AssertionError("unsupported sample rate was accepted")
