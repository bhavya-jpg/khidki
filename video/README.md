# The Khidki explainer video

A motion-graphic explainer of 2 minutes 51 seconds (the hackathon limit is 3 minutes), built with
[Remotion](https://www.remotion.dev/) in Khidki's own design tokens and fonts. Twelve scenes:

1. the question, and 2. the dilemma (shut or open)
3. what Khidki does and who it helps
4. how it decides when, with no hardware: a physics twin, the outdoor forecast and the timetable
5. the school rules as Cedar policies
6. one instruction, one tap (real footage)
7. checking that the window opened: no sensor on the window, one ordinary CO₂ meter (real footage and readings)
8. how it is built on AWS, as an architecture diagram, and 9. the rest of the stack
10. results, 11. what we built, 12. close

What is real in it and what is not:

- **Product footage** (scenes 6 and 7) is the real teacher screen, captured from local mode with
  `scripts/capture.mjs`: a simulated classroom and sensor, real outdoor air (CAMS replay of 18 Nov 2025).
  The "only one side opened" follow-up in scene 7 happened in that run; it was not staged. Its minutes of
  waiting are played faster, and the scene says so.
- **The plan ribbon, the twin's CO₂ forecast, the Cedar decision and the measured CO₂ curve** are drawn
  from that same run's data (`src/data/run.json`).
- **The dilemma numbers** (scene 2) and the twin's constants (scene 4) come from Khidki's physics model, and
  **the results** (scene 10) from
  `docs/benchmark.md`: a simulation on 48 real Delhi days, not a field trial.
- **The window drawings and the architecture diagram** are illustrations. Every box in the diagram is in the
  CDK stack; the AWS console itself is not shown.
- **"No extra hardware"** is said precisely: deciding when to open needs none; checking uses one ordinary
  CO₂ meter (simulated in this demo) and no sensor on the window.
- **The narration is a synthetic voice**, generated on this laptop with
  [Chatterbox](https://github.com/resemble-ai/chatterbox) (Resemble AI, MIT). The last scene says so.
  `tts/check.py` transcribes it back with Whisper to catch a garbled line.

## Rebuild it

```bash
# 1. footage and data (needs local mode running: python tasks.py local partial_open)
node scripts/capture.mjs

# 2. narration (first run downloads about 3 GB of model weights), then cut the footage to it
uv venv --python 3.11 .tts-venv && VIRTUAL_ENV=$PWD/.tts-venv uv pip install chatterbox-tts "setuptools<81" openai-whisper
.tts-venv/bin/python tts/synth.py && .tts-venv/bin/python tts/check.py
node scripts/edit-footage.mjs

# 3. preview, then render
npm install
npx remotion studio
npx remotion render src/index.ts Khidki out/khidki-explainer.mp4
```

The scenes take their length from the narration (`src/data/vo.json`), so re-running step 2 re-times the video.

Remotion is free for individuals and teams of up to three; see its licence before using this elsewhere.
