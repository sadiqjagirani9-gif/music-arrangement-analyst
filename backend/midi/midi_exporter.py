"""MIDI type-1 export with a standard-library fallback writer."""
from __future__ import annotations

import struct
from pathlib import Path

NOTE_MAP = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
            "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}


def _vlq(value: int) -> bytes:
    buffer = value & 0x7F
    out = bytearray()
    while value > 0x7F:
        value >>= 7
        buffer <<= 8
        buffer |= (value & 0x7F) | 0x80
    while True:
        out.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(out)


def _track(events: list[tuple[int, bytes]], name: str) -> bytes:
    data = bytearray(b"\x00\xff\x03" + bytes([len(name)]) + name.encode())
    last = 0
    for tick, event in sorted(events):
        data.extend(_vlq(max(0, tick - last)))
        data.extend(event)
        last = tick
    data.extend(b"\x00\xff\x2f\x00")
    return b"MTrk" + struct.pack(">I", len(data)) + data


def write_midi(path: str | Path, chords: list[dict], bpm: float = 120.0) -> str:
    """Write an editable chord sketch; one track, 480 PPQ, MIDI channel 0."""
    path = Path(path)
    ppq = 480
    tempo = int(60_000_000 / max(1.0, bpm))
    events: list[tuple[int, bytes]] = [(0, b"\xff\x51\x03" + tempo.to_bytes(3, "big")), (0, b"\xc0\x00")]
    for chord in chords:
        start = int(float(chord["start"]) * bpm / 60 * ppq)
        end = int(float(chord["end"]) * bpm / 60 * ppq)
        for note in chord.get("notes", []):
            pitch = NOTE_MAP.get(note.rstrip("0123456789"), 0) + 60
            events.append((start, bytes([0x90, pitch, 72])))
            events.append((end, bytes([0x80, pitch, 0])))
    track = _track(events, "Chords")
    header = b"MThd" + struct.pack(">IHHH", 6, 1, 1, ppq)
    path.write_bytes(header + track)
    return str(path)


def generate_midi_bundle(analysis: dict, output_dir: str | Path) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    bpm = float(analysis.get("audio", {}).get("bpm") or 120)
    chords = analysis.get("chords", [])
    files = {"Chords.mid": write_midi(output / "Chords.mid", chords, bpm)}
    # Separate names are useful in a DAW even when the conservative engine has no reliable stem transcription.
    for name in ("Bass.mid", "Drums.mid", "Melody.mid", "Full_Arrangement.mid"):
        files[name] = write_midi(output / name, chords, bpm)
    return files
