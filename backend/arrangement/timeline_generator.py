from __future__ import annotations

TRACK_ORDER = ["Vocals", "Piano", "Guitar", "Bass", "Drums", "Strings", "Synth", "Other"]


def build_timeline(analysis: dict) -> dict:
    duration = float(analysis.get("audio", {}).get("duration") or 0)
    sections = analysis.get("structure", [])
    instruments = {item["name"]: item for item in analysis.get("instruments", [])}
    tracks = []
    for name in TRACK_ORDER:
        item = instruments.get(name)
        tracks.append({"name": name, "confidence": item["confidence"] if item else 0.0,
                       "segments": [{"start": item["start"], "end": item["end"], "activity": "candidate"}] if item else []})
    matrix = []
    for section in sections:
        active = {name: bool(instruments.get(name)) for name in TRACK_ORDER}
        matrix.append({"section": section["name"], "start": section["start"], "end": section["end"], "tracks": active})
    return {"duration": duration, "bpm": analysis.get("audio", {}).get("bpm"), "tracks": tracks, "sections": sections, "matrix": matrix}
