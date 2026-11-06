from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

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
from backend.midi.midi_exporter import generate_midi_bundle
from backend.separation.stem_separator import separate_stems

DATA_DIR = Path(os.getenv("MA_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def run_analysis(path: str | Path) -> dict:
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
    return result


try:
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="Music Arrangement Analyst", version="0.1.0")
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
    async def analyze(file: UploadFile = File(...)):
        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=DATA_DIR) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_path = Path(tmp.name)
        try:
            result = run_analysis(temp_path)
            target = DATA_DIR / f"{result['id']}.json"
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return JSONResponse(result)
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
    async def separate(file: UploadFile = File(...)):
        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        target = DATA_DIR / f"upload-{uuid.uuid4().hex}{suffix}"
        with target.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        return separate_stems(target, DATA_DIR / "stems")
except ImportError:
    app = None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
