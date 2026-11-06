from __future__ import annotations


def detect_instruments(audio: dict) -> list[dict]:
    # Instruments are candidates, never asserted as ground truth without a model.
    candidates = [("Vocals", "主旋律/叙事中心", 0.28), ("Drums", "节奏支撑", 0.22), ("Bass", "低频支撑", 0.2),
                  ("Piano", "和声铺底候选", 0.18), ("Other", "未分类复合音色", 0.15)]
    duration = audio.get("duration", 0.0)
    return [{"name": name, "function": function, "confidence": confidence, "start": 0.0, "end": duration,
             "range": "unknown", "technique": "待音轨分离/分类模型确认", "basis": "降级候选，不是确定识别结果"}
            for name, function, confidence in candidates]
