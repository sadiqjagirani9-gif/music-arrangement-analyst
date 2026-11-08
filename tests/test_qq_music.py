from __future__ import annotations

import pytest

from backend.sources.manager import AudioSourceManager, AudioUnavailableError
from backend.sources.models import AudioAccess
from backend.sources.qq_music.qq_auth import QQAuth
from backend.sources.qq_music.qq_models import track_from_search_item
from backend.sources.qq_music.qq_search import QQSearchService


def raw_song(pay_play=0):
    return {
        "id": 42, "mid": "song-mid", "title": "测试歌曲", "interval": 245,
        "album": {"mid": "album-mid", "name": "测试专辑"},
        "singer": [{"mid": "artist-mid", "name": "测试歌手"}],
        "file": {"media_mid": "media-mid", "try_begin": 0, "try_end": 60000},
        "pay": {"pay_play": pay_play},
    }


class FakeClient:
    def __init__(self, pay_play=0):
        self.calls = 0
        self.track = track_from_search_item(raw_song(pay_play))

    def search_raw(self, query, page, page_size):
        self.calls += 1
        return {"data": {"song": {"totalnum": 1, "list": [raw_song()]}}}

    def get_song(self, song_id):
        return self.track

    def resolve_audio_access(self, track):
        return AudioAccess("requires_upload", "没有匿名公开音频")


def test_search_parses_metadata_and_cache(tmp_path):
    client = FakeClient()
    search = QQSearchService(client, tmp_path, ttl_seconds=60)
    first = search.search("测试", "all", 1, 10)
    second = search.search("测试", "all", 1, 10)
    assert first.items[0].title == "测试歌曲"
    assert first.items[0].artists == ["测试歌手"]
    assert first.items[0].album == "测试专辑"
    assert first.items[0].cover_url.endswith("album-mid.jpg?max_age=2592000")
    assert second.cached is True
    assert client.calls == 1


@pytest.mark.parametrize("scope", ["song", "artist", "album"])
def test_search_scopes(tmp_path, scope):
    assert QQSearchService(FakeClient(), tmp_path).search("测试", scope, 1, 10).items


def test_restricted_track_requires_local_upload(tmp_path):
    manager = AudioSourceManager(tmp_path, FakeClient(pay_play=1))
    with pytest.raises(AudioUnavailableError) as caught:
        manager.import_qq_track("song-mid", lambda path, source: {})
    assert caught.value.track.source_id == "song-mid"
    assert "公开音频" in caught.value.reason


def test_auth_status_and_invalid_callback(monkeypatch):
    monkeypatch.delenv("QQ_CONNECT_APP_ID", raising=False)
    monkeypatch.delenv("QQ_CONNECT_APP_KEY", raising=False)
    auth = QQAuth()
    assert auth.status().configured is False
    with pytest.raises(RuntimeError, match="state"):
        auth.handle_callback("bad-code", "bad-state")


def test_track_access_marks_member_content():
    track = track_from_search_item(raw_song(pay_play=1))
    assert track.access.status == "requires_upload"
    assert track.extra["pay_play"] == 1
