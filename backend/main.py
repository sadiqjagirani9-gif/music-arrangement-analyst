from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from backend.ai.music_reasoner import build_reasoning
from backend.ai.report_generator import to_markdown
from backend.analyzers.audio_analyzer import analyze_audio
from backend.analyzers.chord_detector import detect_chords
from backend.analyzers.instrument_detector import detect_instruments
from backend.analyzers.key_detector import detect_key
from backend.analyzers.rhythm_analyzer import analyze_rhythm
from backend.analyzers.structure_detector import detect_structure
from backend.arrangement.arrangement_analyzer import arrangement_advice
from backend.arrangement.timeline_generator import build_timeline
from backend.capture.manager import CaptureManager, CaptureStateError
from backend.capture.models import CaptureConfig
from backend.midi.midi_exporter import generate_midi_bundle
from backend.separation.stem_separator import separate_stems
from backend.sources.manager import (
    AudioSourceManager,
    AudioUnavailableError,
    parse_source_metadata,
    sha256_file,
)
from backend.sources.qq_music.qq_auth import QQAuth
from backend.sources.qq_music.qq_client import QQMusicClient, QQMusicError
from backend.sources.qq_music.qq_metadata import QQMetadataService
from backend.sources.qq_music.qq_search import QQSearchService

DATA_DIR = Path(os.getenv("MA_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
qq_client = QQMusicClient()
qq_search = QQSearchService(qq_client, DATA_DIR / "cache" / "qq_music")
qq_metadata = QQMetadataService(qq_client)
qq_auth = QQAuth()
source_manager = AudioSourceManager(DATA_DIR, qq_client)


def run_analysis(path: str | Path, source_metadata: dict | None = None) -> dict:
    audio = analyze_audio(path)
    key = detect_key(audio)
    chords = detect_chords(audio, audio.get("duration", 0.0))
    result = {"id": uuid.uuid4().hex, "audio": audio, "key": key, "chords": chords,
              "rhythm": analyze_rhythm(audio), "structure": detect_structure(audio, chords),
              "instruments": detect_instruments(audio)}
    result["timeline"] = build_timeline(result)
    result["reasoning"] = build_reasoning(result)
    result["advice"] = arrangement_advice(result)
    result["report_markdown"] = to_markdown(result)
    source = source_manager.local_source(source_metadata).to_dict()
    source["audio_hash_sha256"] = source.get("audio_hash_sha256") or sha256_file(path)
    result["source"] = source
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    return result


def save_analysis(result: dict) -> dict:
    target = DATA_DIR / f"{result['id']}.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def analyze_capture(path: Path, metadata: dict) -> dict:
    return save_analysis(run_analysis(path, metadata))


capture_manager = CaptureManager(DATA_DIR / "captures", analyze_capture)


try:
    from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="Music Arrangement Analyst", version="0.3.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    FRONTEND_INDEX = FRONTEND_DIST / "index.html"

    @app.get("/", include_in_schema=False)
    def root():
        if FRONTEND_INDEX.exists():
            return FileResponse(FRONTEND_INDEX)
        return {"service": "music-arrangement-analyst", "status": "ok", "frontend": "run npm run dev in frontend/"}

    if (FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "music-arrangement-analyst"}

    @app.post("/api/analyze")
    async def analyze(
        file: Annotated[UploadFile, File()],
        source_metadata: Annotated[str | None, Form()] = None,
    ):
        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=DATA_DIR) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_path = Path(tmp.name)
        try:
            metadata = parse_source_metadata(source_metadata)
            metadata.setdefault("audio_origin", "local_upload")
            return JSONResponse(save_analysis(run_analysis(temp_path, metadata)))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            temp_path.unlink(missing_ok=True)

    @app.get("/api/analysis/{analysis_id}")
    def get_analysis(analysis_id: str):
        path = DATA_DIR / f"{analysis_id}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="analysis not found")
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/api/analysis/{analysis_id}/report.md")
    def report(analysis_id: str):
        item = get_analysis(analysis_id)
        return PlainTextResponse(item["report_markdown"], media_type="text/markdown")

    @app.post("/api/analysis/{analysis_id}/midi")
    def midi(analysis_id: str):
        item = get_analysis(analysis_id)
        files = generate_midi_bundle(item, DATA_DIR / analysis_id)
        return {"files": files}

    @app.post("/api/separate")
    async def separate(file: Annotated[UploadFile, File()]):
        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        target = DATA_DIR / f"upload-{uuid.uuid4().hex}{suffix}"
        with target.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        return separate_stems(target, DATA_DIR / "stems")

    @app.get("/api/capture/devices")
    def capture_devices():
        devices = capture_manager.list_devices()
        return {"devices": devices, "preferred_backend": "soundcard_wasapi", "supported_sample_rates": [44100, 48000]}

    @app.post("/api/capture/sessions")
    def start_capture(payload: Annotated[dict, Body()]):
        try:
            config = CaptureConfig(
                device_id=str(payload.get("device_id") or ""),
                sample_rate=int(payload.get("sample_rate") or 48000),
                channels=int(payload.get("channels") or 2),
                max_duration_seconds=float(payload["max_duration_seconds"]) if payload.get("max_duration_seconds") else None,
                auto_analyze=bool(payload.get("auto_analyze", True)),
            )
            return capture_manager.start(config)
        except (ValueError, CaptureStateError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/capture/sessions/{session_id}")
    def capture_status(session_id: str):
        try:
            return capture_manager.get(session_id).to_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/capture/sessions/{session_id}/pause")
    def pause_capture(session_id: str):
        try:
            return capture_manager.pause(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CaptureStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/capture/sessions/{session_id}/resume")
    def resume_capture(session_id: str):
        try:
            return capture_manager.resume(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CaptureStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/capture/sessions/{session_id}/stop")
    def stop_capture(session_id: str):
        try:
            return capture_manager.stop(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except CaptureStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/capture/sessions/{session_id}/audio.wav")
    def download_capture(session_id: str):
        try:
            path = capture_manager.path(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if not path.exists() or path.stat().st_size < 44:
            raise HTTPException(status_code=409, detail="录音文件尚未生成")
        return FileResponse(path, media_type="audio/wav", filename=f"live-capture-{session_id}.wav")

    @app.get("/api/sources/qq/search")
    def search_qq(
        q: str = Query(min_length=1, max_length=100),
        scope: str = Query("all", pattern="^(all|song|artist|album)$"),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=50),
    ):
        try:
            return qq_search.search(q, scope, page, page_size).to_dict()
        except (QQMusicError, ValueError) as exc:
            raise HTTPException(status_code=503 if isinstance(exc, QQMusicError) else 422, detail=str(exc)) from exc

    @app.get("/api/sources/qq/songs/{song_id}")
    def qq_song(song_id: str):
        try:
            track = qq_metadata.song(song_id)
            artists = [{"id": artist_id, "name": name} for artist_id, name in zip(track.artist_ids, track.artists)]
            album = {"id": track.album_id, "name": track.album, "cover_url": track.cover_url}
            return {"track": track.to_dict(), "artists": artists, "album": album}
        except QQMusicError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/api/sources/qq/import")
    def import_qq(payload: Annotated[dict, Body()]):
        song_id = str(payload.get("song_id") or "").strip()
        if not song_id:
            raise HTTPException(status_code=422, detail="song_id is required")
        try:
            return save_analysis(source_manager.import_qq_track(song_id, run_analysis))
        except AudioUnavailableError as exc:
            raise HTTPException(status_code=409, detail={"code": "local_upload_required", "message": exc.reason, "track": exc.track.to_dict()}) from exc
        except QQMusicError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/api/sources/qq/auth/status")
    def qq_auth_status():
        return qq_auth.status().to_dict()

    @app.post("/api/sources/qq/auth/start")
    def qq_auth_start():
        try:
            return {"authorization_url": qq_auth.authorization_url(), "note": "QQ Connect 身份授权不授予 QQ 音乐会员音频权限。"}
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/sources/qq/auth/callback")
    def qq_auth_callback(code: str, state: str):
        try:
            return qq_auth.handle_callback(code, state).to_dict()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/sources/qq/auth/logout")
    def qq_auth_logout():
        return qq_auth.logout().to_dict()
except ImportError:
    app = None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
        access_log=False,
    )
