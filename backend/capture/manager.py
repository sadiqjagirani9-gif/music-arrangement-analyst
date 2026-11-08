from __future__ import annotations

import math
import os
import threading
import uuid
import wave
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from backend.capture.devices import WindowsAudioBackend
from backend.capture.models import CaptureConfig
from backend.capture.validation import validate_wav


class CaptureStateError(RuntimeError):
    pass


class CaptureSession:
    def __init__(self, session_id: str, output_path: Path, config: CaptureConfig, device: dict, backend, analyze_callback=None):
        self.id = session_id
        self.output_path = output_path
        self.config = config
        self.device = device
        self.backend = backend
        self.analyze_callback = analyze_callback
        self.state = "starting"
        self.error: str | None = None
        self.frames_written = 0
        self.file_size_bytes = 0
        self.rms = 0.0
        self.peak = 0.0
        self.level_dbfs = -96.0
        self.waveform: list[float] = []
        self.analysis_progress = 0
        self.analysis_id: str | None = None
        self.validation: dict[str, Any] | None = None
        self.created_at = datetime.now(UTC).isoformat()
        self.completed_at: str | None = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"capture-{session_id}", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def pause(self) -> None:
        with self._lock:
            if self.state != "recording":
                raise CaptureStateError("只有录制中的会话可以暂停")
            self._paused.set()
            self.state = "paused"

    def resume(self) -> None:
        with self._lock:
            if self.state != "paused":
                raise CaptureStateError("只有已暂停的会话可以继续")
            self._paused.clear()
            self.state = "recording"

    def stop(self) -> None:
        with self._lock:
            if self.state not in {"starting", "recording", "paused"}:
                raise CaptureStateError("当前会话不能停止")
            self.state = "stopping"
            self._stop.set()

    def wait(self, timeout: float = 30) -> bool:
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _update_metrics(self, data: np.ndarray) -> None:
        mono = data.mean(axis=1) if data.ndim > 1 else data
        rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
        peak = float(np.max(np.abs(data))) if data.size else 0.0
        if mono.size > 160:
            indexes = np.linspace(0, mono.size - 1, 160, dtype=int)
            mono = mono[indexes]
        with self._lock:
            self.rms = rms
            self.peak = peak
            self.level_dbfs = max(-96.0, 20 * math.log10(max(rms, 1e-8)))
            self.waveform = [round(float(value), 5) for value in mono]

    def _normalize_channels(self, data: np.ndarray) -> np.ndarray:
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        if data.shape[1] > self.config.channels:
            data = data[:, :self.config.channels]
        elif data.shape[1] < self.config.channels:
            data = np.repeat(data[:, :1], self.config.channels, axis=1)
        return np.asarray(data, dtype=np.float32)

    def _run(self) -> None:
        blocksize = 2048
        ole32 = None
        try:
            if os.name == "nt":
                import ctypes
                ole32 = ctypes.OleDLL("ole32")
                ole32.CoInitialize(None)
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(self.output_path), "wb") as wav:
                wav.setnchannels(self.config.channels)
                wav.setsampwidth(2)
                wav.setframerate(self.config.sample_rate)
                with self.backend.open_stream(self.config.device_id, self.config.sample_rate, self.config.channels, blocksize) as read:
                    with self._lock:
                        self.state = "recording"
                    while not self._stop.is_set():
                        data = self._normalize_channels(np.asarray(read(blocksize)))
                        self._update_metrics(data)
                        if self._paused.is_set():
                            continue
                        pcm = (np.clip(data, -1.0, 1.0) * 32767).astype("<i2").tobytes()
                        wav.writeframesraw(pcm)
                        with self._lock:
                            self.frames_written += data.shape[0]
                            self.file_size_bytes = 44 + self.frames_written * self.config.channels * 2
                        maximum = self.config.max_duration_seconds
                        if maximum and self.frames_written / self.config.sample_rate >= maximum:
                            self._stop.set()
            with self._lock:
                self.state = "processing"
                self.analysis_progress = 15
                self.file_size_bytes = self.output_path.stat().st_size
            validation = validate_wav(self.output_path)
            with self._lock:
                self.validation = validation.to_dict()
                self.analysis_progress = 30
            if not validation.valid:
                with self._lock:
                    self.state = "invalid"
                    self.analysis_progress = 100
                    self.error = "；".join(validation.issues) + "。若受保护内容无法捕获，请改用合法取得的本地音频。"
                return
            if self.config.auto_analyze and self.analyze_callback:
                with self._lock:
                    self.state = "analyzing"
                    self.analysis_progress = 45
                metadata = {
                    "platform": "live_capture", "source_id": self.id,
                    "title": f"Live Capture {self.created_at}", "artists": [], "album": None,
                    "audio_origin": self.device["kind"], "capture_device": self.device,
                }
                result = self.analyze_callback(self.output_path, metadata)
                with self._lock:
                    self.analysis_id = result["id"]
                    self.analysis_progress = 100
            with self._lock:
                self.state = "completed"
                self.completed_at = datetime.now(UTC).isoformat()
        except Exception as exc:  # noqa: BLE001 - thread boundary must preserve errors in session state
            with self._lock:
                self.state = "error"
                self.error = str(exc)
                self.analysis_progress = 100
        finally:
            if ole32 is not None:
                ole32.CoUninitialize()
            with self._lock:
                if self.completed_at is None and self.state in {"invalid", "error"}:
                    self.completed_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "id": self.id, "state": self.state, "error": self.error,
                "device": self.device, "sample_rate": self.config.sample_rate,
                "channels": self.config.channels,
                "max_duration_seconds": self.config.max_duration_seconds,
                "duration_seconds": round(self.frames_written / self.config.sample_rate, 3),
                "file_size_bytes": self.file_size_bytes, "rms": round(self.rms, 6),
                "peak": round(self.peak, 6), "level_dbfs": round(self.level_dbfs, 2),
                "waveform": self.waveform, "analysis_progress": self.analysis_progress,
                "analysis_id": self.analysis_id, "validation": self.validation,
                "created_at": self.created_at, "completed_at": self.completed_at,
                "download_available": self.output_path.exists() and self.output_path.stat().st_size >= 44,
            }


class CaptureManager:
    def __init__(self, output_dir: str | Path, analyze_callback: Callable[[Path, dict], dict] | None = None, backend=None):
        self.output_dir = Path(output_dir)
        self.analyze_callback = analyze_callback
        self.backend = backend or WindowsAudioBackend()
        self.sessions: dict[str, CaptureSession] = {}
        self._lock = threading.RLock()

    def list_devices(self) -> list[dict]:
        return [device.to_dict() for device in self.backend.list_devices()]

    def start(self, config: CaptureConfig) -> dict:
        config.validate()
        devices = {device["id"]: device for device in self.list_devices()}
        if config.device_id not in devices:
            raise ValueError("所选音频设备不存在或已断开")
        with self._lock:
            if any(session.state in {"starting", "recording", "paused", "stopping", "processing", "analyzing"} for session in self.sessions.values()):
                raise CaptureStateError("已有录制或分析任务正在运行")
            session_id = uuid.uuid4().hex
            session = CaptureSession(session_id, self.output_dir / f"{session_id}.wav", config, devices[config.device_id], self.backend, self.analyze_callback)
            self.sessions[session_id] = session
            session.start()
            return session.to_dict()

    def get(self, session_id: str) -> CaptureSession:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise KeyError("录制会话不存在") from exc

    def pause(self, session_id: str) -> dict:
        session = self.get(session_id)
        session.pause()
        return session.to_dict()

    def resume(self, session_id: str) -> dict:
        session = self.get(session_id)
        session.resume()
        return session.to_dict()

    def stop(self, session_id: str) -> dict:
        session = self.get(session_id)
        session.stop()
        return session.to_dict()

    def path(self, session_id: str) -> Path:
        return self.get(session_id).output_path
