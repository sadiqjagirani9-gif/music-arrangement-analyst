"""Small, dependency-light audio loading helpers.

WAV decoding is implemented with the standard library so the API remains useful
when librosa is not installed. Librosa is used automatically when available for
compressed formats and richer features.
"""
from __future__ import annotations

import audioop
import math
import wave
from pathlib import Path
from typing import Tuple


def load_audio(path: str | Path, target_sr: int = 22050) -> Tuple[list[float], int]:
    """Return mono float samples and sample rate, with an optional librosa path."""
    path = Path(path)
    try:
        import librosa  # type: ignore

        samples, sr = librosa.load(str(path), sr=target_sr, mono=True)
        return samples.astype(float).tolist(), int(sr)
    except (ImportError, ModuleNotFoundError):
        pass
    if path.suffix.lower() != ".wav":
        raise RuntimeError("librosa is required for non-WAV input files")
    with wave.open(str(path), "rb") as wav:
        channels, width, sr, frames = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
        raw = wav.readframes(frames)
    if channels > 1:
        raw = audioop.tomono(raw, width, 0.5, 0.5)
    if sr != target_sr:
        raw, _ = audioop.ratecv(raw, width, 1, sr, target_sr, None)
        sr = target_sr
    scale = float(1 << (8 * width - 1))
    values = [int.from_bytes(raw[i : i + width], "little", signed=True) / scale for i in range(0, len(raw), width)]
    return values, sr


def duration_seconds(samples: list[float], sample_rate: int) -> float:
    return len(samples) / sample_rate if sample_rate else 0.0


def rms(samples: list[float]) -> float:
    return math.sqrt(sum(v * v for v in samples) / len(samples)) if samples else 0.0
