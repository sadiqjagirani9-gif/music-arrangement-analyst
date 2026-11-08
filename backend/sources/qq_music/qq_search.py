from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from backend.sources.qq_music.qq_models import QQSearchPage, track_from_search_item


class QQSearchService:
    def __init__(self, client, cache_dir: str | Path, ttl_seconds: int = 900):
        self.client = client
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds

    def _cache_path(self, query: str, scope: str, page: int, page_size: int) -> Path:
        key = hashlib.sha256(f"{query}|{scope}|{page}|{page_size}".encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    @staticmethod
    def _matches(track, query: str, scope: str) -> bool:
        needle = query.casefold()
        if scope == "song":
            return needle in track.title.casefold()
        if scope == "artist":
            return any(needle in artist.casefold() for artist in track.artists)
        if scope == "album":
            return needle in track.album.casefold()
        return True

    def search(self, query: str, scope: str = "all", page: int = 1, page_size: int = 20) -> QQSearchPage:
        query = query.strip()
        if not query:
            raise ValueError("搜索关键词不能为空")
        if scope not in {"all", "song", "artist", "album"}:
            raise ValueError("scope must be all, song, artist, or album")
        page, page_size = max(1, page), min(50, max(1, page_size))
        cache_path = self._cache_path(query, scope, page, page_size)
        if cache_path.exists() and time.time() - cache_path.stat().st_mtime < self.ttl_seconds:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            items = [track_from_search_item(item) for item in cached["raw_items"]]
            result = QQSearchPage(query, scope, page, page_size, cached["total"], items, cached=True)
            return result
        raw = self.client.search_raw(query, page, page_size)
        song = ((raw.get("data") or {}).get("song") or {})
        raw_items = song.get("list") or []
        parsed = [track_from_search_item(item) for item in raw_items]
        filtered_pairs = [(item, parsed_item) for item, parsed_item in zip(raw_items, parsed) if self._matches(parsed_item, query, scope)]
        result = QQSearchPage(query, scope, page, page_size, int(song.get("totalnum") or len(filtered_pairs)), [pair[1] for pair in filtered_pairs])
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"total": result.total, "raw_items": [pair[0] for pair in filtered_pairs]}, ensure_ascii=False), encoding="utf-8")
        return result
