# Khidki (खिड़की)

**Open the window at the right minute.**

Khidki tells a Delhi teacher exactly when to open or close the classroom windows on a bad-air day, so 40
children breathe less PM2.5 *and* stay below the CO₂ levels that wreck concentration. It plans with a
physics twin of the room, nudges the teacher with one calm instruction, and checks from the CO₂ curve
that the air really changed.

Built for **Environmental Hacks (Bharat Builds Tour), Air track**, 8 to 11 Oct 2026. Work in progress:
see [`docs/SPEC.md`](docs/SPEC.md) for the plan and the git history for progress.

## What it does, in one breath
Every morning Khidki plans each classroom's ventilation in 5-minute steps from the outdoor forecast, the
timetable and a physics model of the room. School safety rules are [Cedar](core/khidki_core/policy/khidki.cedar)
policies (for example S2: outdoor PE moves indoors if forecast PM2.5 is above 90). During the day the teacher
sees one calm Hindi/English instruction. Khidki then reads the CO₂ curve to check the window really opened
(the children's breath is the tracer gas), and asks for the corridor side if only one side did. It re-plans
every 5 minutes, never asks more than 6 times a day, and answers questions in Hindi with numbers it can't
make up.

## Results (simulation with real outdoor air, not a field trial)
Over 48 real East Delhi school days (Oct to Dec 2025), against a CO₂ alarm with the same teacher behaviour,
in a class of 44 without a purifier ([full report](docs/benchmark.md)):

| | CO₂ alarm | Khidki |
|---|---|---|
| Minutes a day above 1,500 ppm | 65 | **17** (fewer on 44 of 48 days) |
| Requests to the teacher a day | 15 | **4** |
| PM2.5 dose (% of an always-open room) | 89% | 93% |

Khidki trades a few points of PM2.5 for far less stuffiness and far fewer interruptions. Weighted towards
PM, it matches the alarm on both PM2.5 and CO₂ with a third of the requests and less than half the cold air.
Without a purifier, physics leaves little room to cut PM by timing alone; we say so in the report.

![Benchmark](docs/benchmark-pareto.png)

## Run locally (no AWS account needed)

```bash
python tasks.py setup            # needs uv (https://docs.astral.sh/uv/) and Node 20+
python tasks.py local            # API + simulator on :8000, web on :5173
python tasks.py local partial_open
```

Then open <http://localhost:5173/teacher/6B>. The classroom is simulated (labelled on screen); the outdoor
air is a real Delhi day from November 2025. Scenarios: `severe_morning`, `partial_open` (you tap the
buttons; only one side really opens), `teacher_cant_cold`, `forecast_spike`, `purifier_room`.

Local mode keeps data in memory. To run it on DynamoDB instead, either on your AWS account or fully offline
on [LocalStack](https://github.com/localstack/localstack):

```bash
docker run -d -p 4566:4566 localstack/localstack
KHIDKI_STORE=dynamo AWS_ENDPOINT_URL=http://localhost:4566 AWS_DEFAULT_REGION=ap-south-1 \
  AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test python tasks.py local
```

The policies are [Cedar](https://www.cedarpolicy.com/) (`core/khidki_core/policy/khidki.cedar`), and "Ask
Khidki" is a [Strands Agents](https://strandsagents.com/) agent; set `KHIDKI_BEDROCK=1` to let it phrase answers
with Amazon Bedrock, otherwise it answers from verified templates.

```bash
python tasks.py test             # Python tests
python tasks.py lint             # ruff + mypy
```

## Built with
- **AI coding tools used:** Claude Code (Anthropic) in VS Code.
- Credits and licences: [`docs/CREDITS.md`](docs/CREDITS.md).

Licence: Apache-2.0.
