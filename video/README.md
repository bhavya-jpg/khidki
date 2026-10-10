# The Khidki explainer video

A motion-graphic explainer of about two and a half minutes, built with [Remotion](https://www.remotion.dev/)
in Khidki's own design tokens and fonts.

What is real in it and what is not:

- **Product footage** (scenes 5 and 6) is the real teacher screen, captured from local mode with
  `scripts/capture.mjs`: a simulated classroom and sensor, real outdoor air (CAMS replay of 18 Nov 2025).
  The "only one side opened" follow-up in scene 6 happened in that run; it was not staged.
- **The plan ribbon, the Cedar decision and the CO₂ curve** are drawn from that same run's data
  (`src/data/run.json`).
- **The dilemma numbers** (scene 2) come from Khidki's physics model, and **the results** (scene 8) from
  `docs/benchmark.md`: a simulation on 48 real Delhi days, not a field trial.
- **The window drawings** are illustrations, with the product's rule: one dot ≈ 2 µg/m³ of PM2.5.
- **The narration is a synthetic voice**, generated on this laptop with
  [Chatterbox](https://github.com/resemble-ai/chatterbox) (Resemble AI, MIT). The last scene says so.
  `tts/check.py` transcribes it back with Whisper to catch a garbled line.

## Rebuild it

```bash
# 1. footage and data (needs local mode running: python tasks.py local partial_open)
node scripts/capture.mjs

# 2. narration (first run downloads about 3 GB of model weights)
uv venv --python 3.11 .tts-venv && VIRTUAL_ENV=$PWD/.tts-venv uv pip install chatterbox-tts "setuptools<81" openai-whisper
.tts-venv/bin/python tts/synth.py && .tts-venv/bin/python tts/check.py

# 3. preview, then render
npm install
npx remotion studio
npx remotion render src/index.ts Khidki out/khidki-explainer.mp4
```

The scenes take their length from the narration (`src/data/vo.json`), so re-running step 2 re-times the video.

Remotion is free for individuals and teams of up to three; see its licence before using this elsewhere.
