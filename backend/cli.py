from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.ai.report_generator import to_markdown
from backend.main import run_analysis
from backend.midi.midi_exporter import generate_midi_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Music Arrangement Analyst local CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze"); analyze.add_argument("input"); analyze.add_argument("--out", default="analysis.json"); analyze.add_argument("--report", default="report.md")
    midi = sub.add_parser("midi"); midi.add_argument("analysis"); midi.add_argument("--out", default="midi")
    args = parser.parse_args()
    if args.command == "analyze":
        result = run_analysis(args.input)
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        Path(args.report).write_text(to_markdown(result), encoding="utf-8")
        print(json.dumps({"analysis": args.out, "report": args.report}, ensure_ascii=False))
    else:
        result = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
        print(json.dumps(generate_midi_bundle(result, args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
