from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.sources.models import AudioAccess, SourceTrack


@dataclass(slots=True)
class QQSearchPage:
    query: str
    scope: str
    page: int
    page_size: int
    total: int
    items: list[SourceTrack]
    cached: bool = False
    api_status: str = "unofficial_web_endpoint"

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query, "scope": self.scope, "page": self.page,
            "page_size": self.page_size, "total": self.total,
            "cached": self.cached, "api_status": self.api_status,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(slots=True)
class QQAuthStatus:
    configured: bool
    authenticated: bool
    expired: bool
    provider: str = "QQ Connect OAuth 2.0"
    grants_music_entitlement: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def track_from_search_item(item: dict[str, Any]) -> SourceTrack:
    album = item.get("album") or {"mid": item.get("albummid"), "name": item.get("albumname")}
    singers = item.get("singer") or []
    file_info = item.get("file") or {}
    pay = item.get("pay") or {}
    song_mid = str(item.get("mid") or item.get("songmid") or "")
    album_mid = str(album.get("mid") or "")
    restricted = bool(pay.get("pay_play"))
    access = AudioAccess(
        status="requires_upload" if restricted else "unchecked",
        reason="该歌曲标记为付费/会员播放，不能直接导入；请上传你合法取得的本地音频。" if restricted else "歌曲可能提供公开播放地址，导入时将再次检查。",
    )
    return SourceTrack(
        source="qq_music", source_id=song_mid,
        title=str(item.get("title") or item.get("name") or "未知歌曲"),
        artists=[str(s.get("name") or s.get("title")) for s in singers if s.get("name") or s.get("title")],
        album=str(album.get("name") or album.get("title") or "未知专辑"),
        duration_seconds=int(item.get("interval") or 0),
        cover_url=f"https://y.qq.com/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else None,
        album_id=album_mid or None,
        artist_ids=[str(s.get("mid")) for s in singers if s.get("mid")],
        media_id=str(file_info.get("media_mid") or file_info.get("strMediaMid") or item.get("strMediaMid") or song_mid) or None,
        public_url=f"https://y.qq.com/n/ryqq/songDetail/{song_mid}" if song_mid else None,
        access=access,
        extra={
            "numeric_id": item.get("id"), "release_date": item.get("time_public"),
            "bpm_metadata": item.get("bpm"), "pay_play": int(pay.get("pay_play") or 0),
            "preview_begin_ms": file_info.get("try_begin"), "preview_end_ms": file_info.get("try_end"),
        },
    )
