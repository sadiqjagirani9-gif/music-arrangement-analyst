from __future__ import annotations


def to_markdown(analysis: dict) -> str:
    audio, key, rhythm = analysis.get("audio", {}), analysis.get("key", {}), analysis.get("rhythm", {})
    lines = ["# Music Arrangement Analyst 报告", "", "## 摘要", f"- 时长：{audio.get('duration', 0)} s",
             f"- BPM：{audio.get('bpm') or '未知'}（置信度 {audio.get('bpm_confidence', 0)}）",
             f"- 调性候选：{key.get('key', 'Unknown')} {key.get('mode', '')}（置信度 {key.get('confidence', 0)}）",
             f"- 拍号候选：{rhythm.get('meter', '未知')}（置信度 {rhythm.get('meter_confidence', 0)}）", "", "## 和声"]
    for chord in analysis.get("chords", []):
        lines.append(f"- {chord['start']:.2f}-{chord['end']:.2f}s：{chord['name']}，音符 {', '.join(chord['notes'])}，置信度 {chord['confidence']}")
    lines += ["", "## 曲式"]
    for section in analysis.get("structure", []):
        lines.append(f"- {section['start']:.2f}-{section['end']:.2f}s：{section['name']}，{section['evidence']}")
    lines += ["", "## 乐器候选"]
    for item in analysis.get("instruments", []):
        lines.append(f"- {item['name']}：{item['function']}，置信度 {item['confidence']}，{item['basis']}")
    lines += ["", "## 限制与建议", "- 结果是编曲草案和分析候选，不承诺完整复原原曲。", "- 对关键和弦、乐器身份和结构边界建议在 DAW 中人工复核。"]
    return "\n".join(lines) + "\n"
