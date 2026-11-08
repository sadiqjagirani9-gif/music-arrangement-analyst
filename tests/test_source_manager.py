from backend.main import run_analysis
from backend.sources.manager import sha256_file
from tests.test_core import make_wav


def test_unified_analysis_persists_source_and_hash(tmp_path):
    path = tmp_path / "source.wav"
    make_wav(path, seconds=0.25)
    result = run_analysis(path, {"source": "qq_music", "source_id": "abc", "title": "测试", "artists": ["歌手"], "album": "专辑"})
    assert result["source"]["platform"] == "qq_music"
    assert result["source"]["source_id"] == "abc"
    assert result["source"]["audio_hash_sha256"] == sha256_file(path)
    assert result["analyzed_at"].endswith("+00:00")
