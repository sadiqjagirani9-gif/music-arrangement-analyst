"""Conservative chord hypotheses; results are labelled as estimates."""
from __future__ import annotations

CHORDS = {
    "maj": {0, 4, 7}, "min": {0, 3, 7}, "dim": {0, 3, 6},
    "sus2": {0, 2, 7}, "sus4": {0, 5, 7}, "7": {0, 4, 7, 10},
    "maj7": {0, 4, 7, 11}, "min7": {0, 3, 7, 10},
}
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def detect_chords(features: dict, duration: float = 0.0, segment_seconds: float = 2.0) -> list[dict]:
    chroma = features.get("features", {}).get("chroma_mean") or []
    if len(chroma) != 12 or duration <= 0:
        return []
    hypotheses = []
    for root in range(12):
        for suffix, tones in CHORDS.items():
            score = sum(chroma[(root + tone) % 12] for tone in tones) / len(tones)
            penalty = sum(chroma[i] for i in range(12) if (i - root) % 12 not in tones) / 12
            hypotheses.append((score - penalty, root, suffix, tones))
    hypotheses.sort(reverse=True)
    score, root, suffix, tones = hypotheses[0]
    count = max(1, round(duration / segment_seconds))
    step = duration / count
    confidence = max(0.0, min(1.0, score * 2.0))
    return [
        {"name": f"{NAMES[root]}{suffix if suffix != 'maj' else ''}", "start": round(i * step, 3),
         "end": round((i + 1) * step, 3), "duration": round(step, 3),
         "notes": [NAMES[(root + tone) % 12] for tone in sorted(tones)],
         "confidence": round(confidence, 3), "evidence": "全曲 chroma 的保守模板匹配；未进行逐帧声部转录。"}
        for i in range(count)
    ]
