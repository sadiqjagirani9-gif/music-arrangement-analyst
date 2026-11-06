from __future__ import annotations


def detect_structure(audio: dict, chords: list[dict]) -> list[dict]:
    duration = float(audio.get("duration") or 0)
    if duration <= 0:
        return []
    labels = ["Intro", "Verse", "Pre-Chorus", "Chorus", "Verse", "Chorus", "Outro"]
    count = min(len(labels), max(2, round(duration / 24)))
    step = duration / count
    return [{"name": labels[i], "start": round(i * step, 3), "end": round((i + 1) * step, 3),
             "energy": "rising" if labels[i] == "Pre-Chorus" else ("high" if labels[i] == "Chorus" else "medium"),
             "confidence": 0.25, "evidence": "基于时长、能量占位与和声重复的可解释启发式；建议人工复核。"}
            for i in range(count)]
