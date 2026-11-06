---
name: music-arrangement-analyst
description: Analyze a local song with Music Arrangement Analyst, explain measurable features and uncertainty, create timeline JSON/Markdown, and export editable MIDI arrangement sketches.
---

# Music Arrangement Analyst

Use this skill when a user asks for song structure, arrangement, harmony, instrument candidates, mix observations, a visual timeline, or a MIDI sketch.

## Local-first workflow

1. Confirm the input path is a user-owned audio file and do not copy it into Git.
2. From the repository root run:

```bash
python -m backend.cli analyze path/to/song.wav --out analysis.json --report report.md
```

3. Generate MIDI drafts:

```bash
python -m backend.cli midi analysis.json --out midi/
```

4. Report each result as one of: measurable algorithm output, model/heuristic inference, or unresolved limitation. Never claim a specific instrument or chord voicing as certain when confidence is low.

## API workflow

Start `uvicorn backend.main:app --reload --port 8000`, upload to `POST /api/analyze`, then use the returned analysis id with `/api/analysis/{id}`, `/report.md`, and `/midi`.

## Safety and copyright

Do not upload API keys, private recordings, model weights, or unlicensed datasets. MIDI files are editable arrangement drafts and must not be described as a complete reconstruction of the source recording.
