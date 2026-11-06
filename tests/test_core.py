import math
import struct
import wave

from backend.analyzers.audio_analyzer import analyze_audio
from backend.analyzers.chord_detector import detect_chords
from backend.analyzers.key_detector import detect_key
from backend.arrangement.timeline_generator import build_timeline
from backend.midi.midi_exporter import generate_midi_bundle


def make_wav(path, seconds=1.0, sr=8000):
    samples = [int(0.2 * 32767 * math.sin(2 * math.pi * 440 * i / sr)) for i in range(int(seconds * sr))]
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(sr)
        out.writeframes(b"".join(struct.pack("<h", x) for x in samples))


def test_audio_and_fallback(tmp_path):
    audio_path = tmp_path / "tone.wav"; make_wav(audio_path)
    result = analyze_audio(audio_path)
    assert result["duration"] > 0.9
    assert result["rms"] > 0


def test_key_chord_timeline_and_midi(tmp_path):
    features = {"features": {"chroma_mean": [1, .1, .8, .1, .9, .1, .1, .8, .1, .9, .1, .1]}}
    key = detect_key(features); assert key["key"] != "Unknown"
    chords = detect_chords({"features": features["features"]}, 8)
    analysis = {"audio": {"duration": 8, "bpm": 120}, "structure": [], "instruments": [], "chords": chords}
    assert build_timeline(analysis)["duration"] == 8
    files = generate_midi_bundle({**analysis}, tmp_path / "midi")
    assert (tmp_path / "midi" / "Chords.mid").read_bytes().startswith(b"MThd")
    assert len(files) == 5
