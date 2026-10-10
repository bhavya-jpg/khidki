"""Check the generated narration: transcribe it back with Whisper, locally, and compare with the script.

A speech model reliably catches a dropped or garbled sentence in 24 lines; a tired listener may not.
Usage: .tts-venv/bin/python tts/check.py
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import whisper

ROOT = Path(__file__).resolve().parents[1]


def norm(text: str) -> list[str]:
    text = (
        text.lower()
        .replace("khidkee", "khidki")
        .replace("a w s", "aws")
        .replace("a p i", "api")
        .replace("a m", "am")
    )
    return re.findall(r"[a-z0-9]+", text)


def main() -> None:
    model = whisper.load_model("base.en")
    scenes = json.loads((ROOT / "tts" / "narration.json").read_text())
    worst = 1.0
    for scene in scenes:
        wav = ROOT / "public" / "vo" / f"{scene['id']}.wav"
        if not wav.exists():
            print(f"{scene['id']}: missing")
            continue
        heard = model.transcribe(str(wav), fp16=False, language="en")["text"].strip()
        want = " ".join(line["say"] for line in scene["lines"])
        ratio = difflib.SequenceMatcher(None, norm(want), norm(heard)).ratio()
        worst = min(worst, ratio)
        flag = "" if ratio >= 0.9 else "   <-- listen to this one"
        print(f"{scene['id']}: {ratio:.2f}{flag}\n   heard: {heard}")
    print(f"lowest match: {worst:.2f}")


if __name__ == "__main__":
    main()
