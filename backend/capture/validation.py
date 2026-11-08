from __future__ import annotations

import audioop
import math
import wave
from pathlib import Path

from backend.capture.models import AudioValidation


def validate_wav(path: str | Path, silence_threshold: float = 0.001, min_duration: float = 0.5) -> AudioValidation:
    path = Path(path)
    issues: list[str] = []
    if not path.exists() or path.stat().st_size < 44:
        return AudioValidation(False, 0, 0, 0, 0, 0, path.stat().st_size if path.exists() else 0, 0, 0, 1, 0, 0, ["WAV 文件不存在或不完整"])
    try:
        wav = wave.open(str(path), "rb")  # noqa: SIM115 - open errors are converted to validation results
    except (wave.Error, EOFError) as exc:
        return AudioValidation(False, 0, 0, 0, 0, 0, path.stat().st_size, 0, 0, 1, 0, 0, [f"WAV 文件无法读取：{exc}"])
    with wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.getnframes()
        duration = frames / rate if rate else 0.0
        chunk_frames = max(1, rate // 2)
        rms_values: list[float] = []
        peak = 0.0
        clipped = 0
        total_samples = 0
        current_silence = 0.0
        longest_silence = 0.0
        silent_chunks = 0
        while raw := wav.readframes(chunk_frames):
            chunk_rms = audioop.rms(raw, width) / float(1 << (width * 8 - 1))
            chunk_peak = audioop.max(raw, width) / float((1 << (width * 8 - 1)) - 1)
            rms_values.append(chunk_rms)
            peak = max(peak, chunk_peak)
            chunk_duration = len(raw) / max(1, rate * channels * width)
            if chunk_rms < silence_threshold:
                silent_chunks += 1
                current_silence += chunk_duration
                longest_silence = max(longest_silence, current_silence)
            else:
                current_silence = 0.0
            sample_count = len(raw) // width
            total_samples += sample_count
            if width == 2:
                for index in range(0, len(raw), 2):
                    if abs(int.from_bytes(raw[index:index + 2], "little", signed=True)) >= 32760:
                        clipped += 1
        overall_rms = math.sqrt(sum(value * value for value in rms_values) / len(rms_values)) if rms_values else 0.0
        silent_ratio = silent_chunks / len(rms_values) if rms_values else 1.0
        clipping_ratio = clipped / total_samples if total_samples else 0.0
    if rate not in {44100, 48000}:
        issues.append(f"不支持的采样率：{rate} Hz")
    if duration < min_duration:
        issues.append(f"录音过短：{duration:.2f} 秒")
    if overall_rms < silence_threshold:
        issues.append("未检测到有效音频，录音接近静音")
    if silent_ratio > 0.9 and duration >= 2:
        issues.append("超过 90% 的录音为静音")
    if longest_silence >= 10:
        issues.append(f"检测到 {longest_silence:.1f} 秒连续静音")
    if clipping_ratio > 0.01:
        issues.append("超过 1% 的采样发生削波")
    return AudioValidation(not any("不支持" in issue or "过短" in issue or "有效音频" in issue or "超过 90%" in issue for issue in issues), round(duration, 3), rate, channels, width, frames, path.stat().st_size, round(overall_rms, 6), round(peak, 6), round(silent_ratio, 4), round(longest_silence, 3), round(clipping_ratio, 6), issues)
