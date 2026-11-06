from __future__ import annotations


def analyze_rhythm(audio: dict) -> dict:
    bpm = audio.get("bpm")
    confidence = audio.get("bpm_confidence", 0.0)
    return {"bpm": bpm, "confidence": confidence, "meter": "4/4 (heuristic)", "meter_confidence": round(confidence * 0.6, 3),
            "groove": "steady" if confidence >= 0.35 else "unknown",
            "evidence": "节拍跟踪器结果；拍号为启发式推断。"}
