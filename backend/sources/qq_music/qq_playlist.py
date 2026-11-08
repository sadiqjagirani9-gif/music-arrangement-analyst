from __future__ import annotations

from backend.sources.qq_music.qq_models import track_from_search_item


class QQPlaylistService:
    def __init__(self, client):
        self.client = client

    def get(self, playlist_id: str) -> dict:
        raw = self.client.get_playlist_raw(playlist_id)
        entries = raw.get("cdlist") or []
        if not entries:
            return {"id": playlist_id, "title": "", "description": "", "tracks": []}
        playlist = entries[0]
        return {
            "id": playlist_id,
            "title": playlist.get("dissname") or "",
            "description": playlist.get("desc") or "",
            "cover_url": playlist.get("logo"),
            "tracks": [track_from_search_item(item).to_dict() for item in playlist.get("songlist") or []],
        }
