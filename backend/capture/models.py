from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class CaptureDevice:
    id: str
    name: str
    backend: str
    kind: str
    is_loopback: bool
    is_default: bool = False
    max_channels: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CaptureConfig:
    device_id: str
    sample_rate: int = 48000
    channels: int = 2
    max_duration_seconds: float | None = None
    auto_analyze: bool = True

    def validate(self) -> None:
        if self.sample_rate not in {44100, 48000}:
            raise ValueError("sample_rate must be 44100 or 48000")
        if self.channels not in {1, 2}:
            raise ValueError("channels must be 1 or 2")
        if self.max_duration_seconds is not None and not 1 <= self.max_duration_seconds <= 14400:
            raise ValueError("max_duration_seconds must be between 1 and 14400")


@dataclass(slots=True)
class AudioValidation:
    valid: bool
    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width_bytes: int
    frame_count: int
    file_size_bytes: int
    rms: float
    peak: float
    silent_ratio: float
    longest_silence_seconds: float
    clipping_ratio: float
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
