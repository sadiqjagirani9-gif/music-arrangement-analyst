from __future__ import annotations

import json
import random
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, ClassVar

from backend.sources.models import AudioAccess, SourceTrack
from backend.sources.qq_music.qq_models import track_from_search_item


class QQMusicError(RuntimeError):
    pass


class QQMusicClient:
    """Isolated client for QQ Music's unofficial web endpoints.

    These endpoints are used by QQ Music web pages but are not documented as a
    stable official third-party API. No cookie, account password, or member-only
    audio URL is accepted or generated here.
    """

    search_url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    song_url = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
    playlist_url = "https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
    gateway_url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    headers: ClassVar[dict[str, str]] = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/", "Origin": "https://y.qq.com"}

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        request_url = f"{url}?{urllib.parse.urlencode(params)}"
        try:
            request = urllib.request.Request(request_url, headers=self.headers)
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise QQMusicError(f"QQ 音乐接口暂时不可用：{exc}") from exc

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={**self.headers, "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise QQMusicError(f"QQ 音乐接口暂时不可用：{exc}") from exc

    def search_raw(self, query: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self._get(self.search_url, {"w": query, "p": page, "n": page_size, "format": "json", "new_json": 1, "cr": 1})

    def get_song(self, song_id: str) -> SourceTrack:
        raw = self._get(self.song_url, {"songmid": song_id, "format": "json"})
        data = raw.get("data") or []
        if not data:
            raise QQMusicError("未找到该 QQ 音乐歌曲")
        return track_from_search_item(data[0])

    def get_playlist_raw(self, playlist_id: str) -> dict[str, Any]:
        return self._get(self.playlist_url, {"type": 1, "json": 1, "utf8": 1, "onlysong": 0, "disstid": playlist_id, "format": "json"})

    def resolve_audio_access(self, track: SourceTrack) -> AudioAccess:
        if int(track.extra.get("pay_play") or 0) != 0:
            return AudioAccess("requires_upload", "该歌曲需要付费或会员播放；不会绕过访问限制，请上传你合法取得的本地音频。")
        if not track.media_id:
            return AudioAccess("requires_upload", "歌曲元数据不包含可解析的媒体标识，请上传本地音频。")
        guid = str(random.randint(1000000000, 9999999999))
        filename = f"C400{track.media_id}.m4a"
        payload = {
            "comm": {"ct": 24, "cv": 0},
            "req_0": {"module": "vkey.GetVkeyServer", "method": "CgiGetVkey", "param": {
                "guid": guid, "songmid": [track.source_id], "songtype": [0], "uin": "0",
                "loginflag": 1, "platform": "20", "filename": [filename],
            }},
        }
        raw = self._post(self.gateway_url, payload)
        data = (raw.get("req_0") or {}).get("data") or {}
        info = (data.get("midurlinfo") or [{}])[0]
        purl = info.get("purl") or ""
        sip = data.get("sip") or []
        if not purl or not sip:
            return AudioAccess("requires_upload", "QQ 音乐没有为当前匿名会话提供公开音频，请上传本地音频。")
        return AudioAccess("available", "QQ 音乐返回了无需会员凭据的公开播放地址。", f"{sip[0]}{purl}", preview=False)
