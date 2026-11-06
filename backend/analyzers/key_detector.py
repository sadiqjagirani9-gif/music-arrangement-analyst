"""Key estimation using chroma correlation, with an explicit confidence score."""
from __future__ import annotations

MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def detect_key(features: dict) -> dict:
    chroma = features.get("features", {}).get("chroma_mean") or []
    if len(chroma) != 12:
        return {"key": "Unknown", "mode": "unknown", "confidence": 0.0, "evidence": "缺少 12 维 chroma"}
    best = ("Unknown", "unknown", -1.0)
    total = sum(chroma) or 1.0
    for root in range(12):
        for mode, scale in (("major", MAJOR), ("minor", MINOR)):
            in_scale = sum(chroma[(root + i) % 12] for i in scale) / total
            out_scale = sum(chroma[i] for i in range(12) if (i - root) % 12 not in scale) / total
            score = in_scale - 0.5 * out_scale
            if score > best[2]:
                best = (NAMES[root], mode, score)
    return {"key": best[0], "mode": best[1], "confidence": round(max(0.0, min(1.0, best[2])), 3), "evidence": "chroma 与调式音级集合相关性"}
