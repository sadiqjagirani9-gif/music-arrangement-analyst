"""Extract measurable audio features with optional librosa acceleration."""
from __future__ import annotations

import math
from pathlib import Path
from statistics import mean

from backend.utils.audio_loader import duration_seconds, load_audio, rms


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))]


def analyze_audio(path: str | Path) -> dict:
    samples, sr = load_audio(path)
    result = {
        "sample_rate": sr,
        "duration": round(duration_seconds(samples, sr), 3),
        "channels": 1,
        "bpm": None,
        "bpm_confidence": 0.0,
        "rms": round(rms(samples), 6),
        "dynamic_range_db": None,
        "features": {},
        "limitations": [],
    }
    try:
        import librosa  # type: ignore

        import numpy as np  # type: ignore

        y = np.asarray(samples, dtype=float)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        tempo_value = float(np.asarray(tempo).reshape(-1)[0])
        frame_rms = librosa.feature.rms(y=y)[0]
        db = librosa.amplitude_to_db(np.maximum(frame_rms, 1e-8), ref=1.0)
        result.update(
            bpm=round(tempo_value, 2),
            bpm_confidence=round(min(1.0, len(beats) / max(1.0, result["duration"] * 2)), 3),
            dynamic_range_db=round(float(np.percentile(db, 95) - np.percentile(db, 5)), 2),
            features={
                "spectral_centroid_hz": round(float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))), 2),
                "spectral_bandwidth_hz": round(float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))), 2),
                "spectral_rolloff_hz": round(float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))), 2),
                "zero_crossing_rate": round(float(np.mean(librosa.feature.zero_crossing_rate(y))), 6),
                "mfcc_mean": [round(float(v), 3) for v in np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13), axis=1)],
                "chroma_mean": [round(float(v), 4) for v in np.mean(librosa.feature.chroma_stft(y=y, sr=sr), axis=1)],
                "onset_strength_mean": round(float(np.mean(librosa.onset.onset_strength(y=y, sr=sr))), 4),
            },
        )
    except (ImportError, ModuleNotFoundError):
        # A deterministic fallback still provides useful level statistics.
        frame = max(1, int(sr * 0.05))
        levels = [rms(samples[i : i + frame]) for i in range(0, len(samples), frame)]
        positive = [20 * math.log10(max(x, 1e-8)) for x in levels]
        result["dynamic_range_db"] = round(_percentile(positive, 0.95) - _percentile(positive, 0.05), 2)
        result["limitations"].append("librosa 未安装：仅返回 WAV 电平统计，频谱与节拍特征不可用。")
    return result
