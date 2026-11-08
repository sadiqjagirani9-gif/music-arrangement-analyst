from __future__ import annotations

from backend.sources.models import SourceTrack


class QQMetadataService:
    def __init__(self, client):
        self.client = client

    def song(self, song_id: str) -> SourceTrack:
        return self.client.get_song(song_id)

    def artist_summary(self, song_id: str) -> list[dict]:
        track = self.song(song_id)
        return [{"id": artist_id, "name": name} for artist_id, name in zip(track.artist_ids, track.artists)]

    def album_summary(self, song_id: str) -> dict:
        track = self.song(song_id)
        return {"id": track.album_id, "name": track.album, "cover_url": track.cover_url}
