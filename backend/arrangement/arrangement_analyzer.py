from __future__ import annotations


def arrangement_advice(analysis: dict) -> list[str]:
    audio, key, rhythm = analysis.get("audio", {}), analysis.get("key", {}), analysis.get("rhythm", {})
    advice = [f"速度：{rhythm.get('bpm') or '未知'} BPM；拍号 {rhythm.get('meter', '未知')}。",
              f"调性候选：{key.get('key', 'Unknown')} {key.get('mode', '')}（置信度 {key.get('confidence', 0):.2f}）。"]
    if audio.get("dynamic_range_db") is not None:
        advice.append(f"可测动态范围约 {audio['dynamic_range_db']} dB；混音压缩/响度判断需要原始多轨才能确认。")
    advice.extend(["和声：先用识别和弦作为可编辑草案，再在 DAW 中按耳朵修正转位与经过和弦。",
                   "编曲：副歌可增加低频支撑与高频填充，具体进入点以时间轴区段和真实音轨为准。"])
    return advice
