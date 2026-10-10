"""Voice the narration with Chatterbox (Resemble AI, MIT licence), fully on this laptop.

Usage: .tts-venv/bin/python tts/synth.py [scene_id ...]
       TTS_RETAKE=s2_dilemma:2,s3_khidki:0 .tts-venv/bin/python tts/synth.py s2_dilemma s3_khidki
       (records four takes of those lines and keeps the one that transcribes back most exactly)

Reads tts/narration.json. Each scene has lines with a spoken form ("say", numbers and acronyms spelled the
way they should sound) and a caption form ("show"). Every line is generated on its own, trimmed, and joined
with a short pause, because the model is steadier on single sentences. Writes public/vo/<scene>.wav and
src/data/vo.json (when each caption starts and ends), which the video reads for its timing.

The voice is synthetic. The video says so on screen.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import torch
import torchaudio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "vo"
TIMING = ROOT / "src" / "data" / "vo.json"
SEEDS = ROOT / "tts" / "seeds.json"  # the take kept for each line, so a rebuild sounds the same
SEED = 11
GAP_S = 0.32  # pause between sentences
LEAD_S = 0.25  # silence before the first word of a scene
TAIL_S = 0.45  # silence after the last word
# Chatterbox's default voice reads fast (about 3.6 words a second at cfg_weight 0.5). A lower cfg_weight
# gives a slower, more deliberate delivery, which a narration over diagrams needs.
CFG_WEIGHT = float(os.environ.get("TTS_CFG", "0.3"))
EXAGGERATION = float(os.environ.get("TTS_EXAGGERATION", "0.35"))
TEMPO = float(os.environ.get("TTS_TEMPO", "0.9"))  # then eased a further 10%: about 3 words a second


GEN = {"exaggeration": EXAGGERATION, "cfg_weight": CFG_WEIGHT, "temperature": 0.65}


def trim(wav: torch.Tensor, sr: int, floor: float = 0.012) -> torch.Tensor:
    """Cut leading and trailing near-silence, keeping 40 ms of air on each side."""
    mono = wav.abs().max(dim=0).values
    loud = (mono > floor).nonzero()
    if loud.numel() == 0:
        return wav
    pad = int(0.04 * sr)
    return wav[:, max(int(loud[0]) - pad, 0) : min(int(loud[-1]) + pad, wav.shape[-1])]


def slow(wav: torch.Tensor, sr: int) -> torch.Tensor:
    """Stretch the line to TEMPO of its speed without changing pitch (ffmpeg's atempo filter)."""
    if abs(TEMPO - 1.0) < 0.005:
        return wav
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "a.wav", Path(tmp) / "b.wav"
        torchaudio.save(str(a), wav, sr)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(a), "-filter:a", f"atempo={TEMPO}", str(b)],
            check=True,
        )
        out, _ = torchaudio.load(str(b))
    return out


_whisper = None


def clarity(wav: torch.Tensor, sr: int, text: str) -> float:
    """How closely a take transcribes back to its line (Whisper): used to choose between retakes."""
    global _whisper
    import difflib
    import re

    import whisper

    if _whisper is None:
        _whisper = whisper.load_model("base.en")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "take.wav"
        torchaudio.save(str(path), wav, sr)
        heard = _whisper.transcribe(str(path), fp16=False, language="en")["text"]
    words = lambda t: re.findall(r"[a-z0-9]+", t.lower().replace("khidkee", "khidki"))  # noqa: E731
    return difflib.SequenceMatcher(None, words(text), words(heard)).ratio()


def main() -> None:
    from chatterbox.tts import ChatterboxTTS

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"loading Chatterbox on {device}…", flush=True)
    model = ChatterboxTTS.from_pretrained(device=device)
    sr = model.sr
    scenes = json.loads((ROOT / "tts" / "narration.json").read_text())
    only = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    timing = json.loads(TIMING.read_text()) if TIMING.exists() else {}
    seeds: dict[str, int] = json.loads(SEEDS.read_text()) if SEEDS.exists() else {}
    retake = {k for k in os.environ.get("TTS_RETAKE", "").split(",") if k}
    for scene in scenes:
        if only and scene["id"] not in only:
            continue
        parts: list[torch.Tensor] = [torch.zeros(1, int(LEAD_S * sr))]
        lines = []
        t = LEAD_S
        for k, line in enumerate(scene["lines"]):
            key = f"{scene['id']}:{k}"
            takes = [SEED + k] if key not in retake else [SEED + k, 101 + k, 211 + k, 307 + k]
            if key in seeds and key not in retake:
                takes = [seeds[key]]
            best: tuple[float, int, torch.Tensor] | None = None
            for seed in takes:
                torch.manual_seed(seed)
                cand = model.generate(line["say"], **GEN).cpu()
                cand = slow(trim(cand, sr), sr)
                score = clarity(cand, sr, line["say"]) if len(takes) > 1 else 1.0
                if len(takes) > 1:
                    print(f"  {key} seed {seed}: {score:.2f}", flush=True)
                if best is None or score > best[0]:
                    best = (score, seed, cand)
            assert best is not None
            seeds[key] = best[1]
            wav = best[2]
            dur = wav.shape[-1] / sr
            lines.append({"text": line["show"], "start": round(t, 3), "end": round(t + dur, 3)})
            parts.append(wav)
            t += dur
            if k + 1 < len(scene["lines"]):
                parts.append(torch.zeros(1, int(GAP_S * sr)))
                t += GAP_S
        parts.append(torch.zeros(1, int(TAIL_S * sr)))
        full = torch.cat(parts, dim=-1)
        peak = float(full.abs().max())
        if peak > 0:
            full = full * (0.89 / peak)  # consistent level across scenes
        torchaudio.save(str(OUT / f"{scene['id']}.wav"), full, sr)
        timing[scene["id"]] = {"seconds": round(full.shape[-1] / sr, 3), "lines": lines}
        print(f"{scene['id']}: {timing[scene['id']]['seconds']} s, {len(lines)} lines", flush=True)
        TIMING.parent.mkdir(parents=True, exist_ok=True)
        TIMING.write_text(json.dumps(timing, indent=1, ensure_ascii=False))
        SEEDS.write_text(json.dumps(seeds, indent=1))
    total = sum(v["seconds"] for v in timing.values())
    print(f"total narration: {total:.1f} s", flush=True)


if __name__ == "__main__":
    main()
