from __future__ import annotations

import hashlib
import json
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

from backend.sources.models import AudioSource, SourceTrack


class AudioUnavailableError(RuntimeError):
    def __init__(self, track: SourceTrack, reason: str):
        super().__init__(reason)
        self.track = track
        self.reason = reason


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AudioSourceManager:
    """Normalizes local and remote sources before invoking the existing engine."""

    def __init__(self, data_dir: str | Path, qq_client=None):
        self.data_dir = Path(data_dir)
        self.qq_client = qq_client

    @staticmethod
    def local_source(metadata: dict | None = None) -> AudioSource:
        metadata = metadata or {}
        return AudioSource(
            platform=metadata.get("source") or metadata.get("platform") or "local",
            source_id=metadata.get("source_id"),
            title=metadata.get("title"),
            artists=list(metadata.get("artists") or []),
            album=metadata.get("album"),
            cover_url=metadata.get("cover_url"),
            audio_origin=metadata.get("audio_origin") or "local_upload",
        )

    def import_qq_track(self, song_id: str, analyze: Callable[[Path, dict], dict]) -> dict:
        if self.qq_client is None:
            raise RuntimeError("QQ Music client is not configured")
        track = self.qq_client.get_song(song_id)
        access = self.qq_client.resolve_audio_access(track)
        track.access = access
        if access.status != "available" or not access.stream_url:
            raise AudioUnavailableError(track, access.reason)
        suffix = ".m4a" if ".m4a" in access.stream_url.lower() else ".mp3"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=self.data_dir) as tmp:
            path = Path(tmp.name)
        try:
            request = urllib.request.Request(access.stream_url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"})
            with urllib.request.urlopen(request, timeout=30) as response, path.open("wb") as handle:
                content_length = int(response.headers.get("Content-Length") or 0)
                if content_length > 50 * 1024 * 1024:
                    raise AudioUnavailableError(track, "公开音频超过 50 MB 安全限制，请改用本地上传")
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 50 * 1024 * 1024:
                        raise AudioUnavailableError(track, "公开音频超过 50 MB 安全限制，请改用本地上传")
                    handle.write(chunk)
            source = AudioSource(
                platform="qq_music", source_id=track.source_id, title=track.title, artists=track.artists,
                album=track.album, cover_url=track.cover_url, audio_origin="qq_public_stream",
                audio_hash_sha256=sha256_file(path),
            )
            return analyze(path, source.to_dict())
        finally:
            path.unlink(missing_ok=True)


def parse_source_metadata(value: str | None) -> dict:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise TypeError("source_metadata must be a JSON object")
    return parsed
