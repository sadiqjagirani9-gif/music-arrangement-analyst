from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class AudioAccess:
    status: str
    reason: str
    stream_url: str | None = None
    preview: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.stream_url:
            data["stream_url"] = self.stream_url
        return data


@dataclass(slots=True)
class SourceTrack:
    source: str
    source_id: str
    title: str
    artists: list[str]
    album: str
    duration_seconds: int
    cover_url: str | None = None
    album_id: str | None = None
    artist_ids: list[str] = field(default_factory=list)
    media_id: str | None = None
    public_url: str | None = None
    access: AudioAccess = field(default_factory=lambda: AudioAccess("unknown", "尚未检查音频访问权限"))
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["access"] = self.access.to_dict()
        return data


@dataclass(slots=True)
class AudioSource:
    platform: str
    source_id: str | None
    title: str | None
    artists: list[str]
    album: str | None
    cover_url: str | None
    audio_origin: str
    audio_hash_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
