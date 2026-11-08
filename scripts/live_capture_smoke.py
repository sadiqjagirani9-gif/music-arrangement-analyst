"""Manual Windows smoke test for loopback capture, analysis, and MIDI export."""
from __future__ import annotations

import json
import time

import numpy as np
import sounddevice as sd

from backend.capture.manager import CaptureManager
from backend.capture.models import CaptureConfig
from backend.main import DATA_DIR, run_analysis, save_analysis
from backend.midi.midi_exporter import generate_midi_bundle


def main() -> None:
    analyzed: dict = {}

    def analyze(path, metadata):
        result = save_analysis(run_analysis(path, metadata))
        analyzed["result"] = result
        return result

    manager = CaptureManager(DATA_DIR / "captures", analyze)
    devices = manager.list_devices()
    device = next((item for item in devices if item["is_default"] and item["is_loopback"]), None)
    device = device or next((item for item in devices if item["is_loopback"]), None)
    if device is None:
        raise RuntimeError("没有检测到 WASAPI Loopback 设备")
    session = manager.start(CaptureConfig(device["id"], 48000, 2, max_duration_seconds=3, auto_analyze=True))
    current = manager.get(session["id"])
    deadline = time.time() + 10
    while current.state == "starting" and time.time() < deadline:
        time.sleep(0.05)
    if current.state != "recording":
        raise RuntimeError(current.error or f"录制无法启动：{current.state}")
    samples = np.arange(48000 * 2)
    tone = (0.12 * np.sin(2 * np.pi * 440 * samples / 48000)).astype(np.float32)
    stereo = np.repeat(tone[:, None], 2, axis=1)
    sd.play(stereo, samplerate=48000, blocking=True)
    deadline = time.time() + 120
    while current.state not in {"completed", "invalid", "error"} and time.time() < deadline:
        time.sleep(0.2)
    if current.state != "completed":
        raise RuntimeError(current.error or f"捕获流程未完成：{current.state}")
    result = analyzed["result"]
    midi_files = generate_midi_bundle(result, DATA_DIR / current.id / "midi")
    status = current.to_dict()
    status.pop("waveform", None)
    print(json.dumps({
        "capture": status,
        "analysis_id": result["id"],
        "analysis_duration": result["audio"]["duration"],
        "source": result["source"],
        "midi_files": sorted(midi_files),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
