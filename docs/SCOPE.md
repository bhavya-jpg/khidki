# Khidki-lite scope (overrides SPEC.md)

Decided Fri 9 Oct 2026, ~22:30 IST, to finish, film and submit by **Sun 11 Oct 10:00 IST**. Everything here
overrides `docs/SPEC.md` where they conflict. All SPEC §19 guardrails still apply (honesty labels, no child
PII, the LLM never decides, frequent commits, no history rewriting).

## KEEP (P0, must work in the video)
- **core/**: physics box model (exact discretisation), dose, CPCB AQI + indicative GRAP, baselines (always
  closed, always open, CO₂ alarm, temperature-led teacher), state estimate + window inference from the CO₂ curve.
- **Optimizer**: 5-minute DP as in SPEC §8.1 with the 6-change cap. *Decision pending:* the scope note asked to
  replace the Lagrangian bisection with "fixed μ, double up to 3 times, truncate". The bisection is already
  built, tested and fast (0.9 s / 1.9 s per re-plan), with a μ floor and a hold-current-state fallback, so it
  stays unless the team says otherwise.
- **Cedar**: S1–S4 plus principal-only override (A1–A3). Fired policy ids are stored and shown in the UI.
- **One Step Functions state machine**: NudgeSM with `waitForTaskToken` → wait → verify from the CO₂ curve →
  VERIFIED / PARTIAL follow-up / NOT_FOLLOWED → re-plan. The AWS centrepiece of the video.
- **Daily plan**: EventBridge Scheduler (06:00 Asia/Kolkata) → planner Lambda directly. No DailyPlanSM.
- **Ingest**: API Gateway HTTP route `POST /v1/ingest` with a device key (in SSM). No IoT Core, no X.509.
- **Agent**: Strands agent on Bedrock (Nova 2 Lite) with read-only tools, the number-fidelity guard, and a
  template fallback that says it is a template.
- **Polly** Hindi (Kajal, neural) for instruction phrases and the principal's morning brief, cached in S3.
- **Local mode**: `python tasks.py local` runs everything with no AWS account (template agent, in-memory store).
  Our "Build It" path and our safety net.
- **Benchmark**: cached Oct–Dec 2025 Delhi school days through the twin under all 5 policies →
  `docs/benchmark.md` + one Pareto PNG, every result labelled "simulation with real outdoor data, not a field
  trial". (Done; also carries a PM-weight sweep and a perfect-compliance row.)

## KEEP (P0, web: React + Vite)
- **Teacher** `/teacher/:roomId`: AirWindow (Canvas2D, calm), one instruction, "I've opened them" / "Can't
  right now" + reasons, Hindi/English, 1024×600 and phone.
- **Principal** `/school/:schoolId`: room list with state and "needs action", outdoor forecast chart, today's
  activity decisions with the Cedar policy and number, logged override form. No SVG facade.
- **Printable window timetable** `/print/:roomId`: the day's plan on one A4 page (Hindi + English, times,
  action, one-line reason). The no-hardware tier.
- **Parent digest** `/parent/:token`: class-level only, two sentences + Polly play button.
- **Results** `/lab`: benchmark table + Pareto image + one replay chart (CO₂ and PM small multiples).
- **Landing** `/`: static hero, still/looping AirWindow, two buttons, how-it-works. No GSAP, no scroll
  scrubbing, no WebGL anywhere.
- **Design**: §14.3 tokens + Anek Latin/Devanagari. (A redesign on 9 Oct added scene-based windows, an air
  ribbon and a landing page within these limits; see `docs/design.md`.)

## NEW (P0)
- `scripts/probe_cpcb.py`: one call to data.gov.in real-time AQI with our key; if unavailable or useless,
  bias correction stays r = 1 and the UI says "uncorrected forecast".
- `scripts/import_real_co2.py`: import a CSV (timestamp, co2_ppm) from a consumer CO₂ meter, run window
  inference, output a chart + inferred states + implied air-change rates, stored as `simulated: false` /
  "real measurement, our hostel room, <date>", shown as a "Real room test" card on `/lab`. **No real data by
  Sat 18:00 → no card. Never fake it.**
- `scripts/smoke_bedrock.py`: one Converse call to Nova 2 Lite, global profile first, then fallbacks; prints
  which worked.

## CUT (do not build; not claimed in README)
IoT Core and the IoT Device SDK, DailyPlanSM, NightlySM (calibration becomes a one-off script shown as a
card), Cognito (demo passcodes + Cedar), AppSync Events (5-second polling), Transcribe, SES,
WebGL/OGL/regl, GSAP/ScrollTrigger/Lenis, KaTeX, Lighthouse budgets, a Playwright screenshot QA loop,
ESP32 firmware, OpenAQ, the five-window Lab animation, the SVG school facade.

## AWS footprint after the cut (each shown in the video)
Lambda, API Gateway, DynamoDB, Step Functions, EventBridge Scheduler, Bedrock, Polly, S3, Amplify Hosting (or
S3 static hosting if Amplify is blocked), CloudWatch. AWS open source: Strands Agents, Cedar, Powertools for
AWS Lambda; moto for tests. IaC: AWS CDK (Python).

## Facts found after the cut (Fri 9 Oct, late)
- **Region: Sydney (`ap-southeast-2`), not Mumbai.** The account uses AWS's new sign-up experience, whose
  managed "RegionFloor" policy denies almost everything outside the account's selected home region. That
  region is `ap-southeast-2`; everything we need works there (checked: Lambda, Step Functions, Scheduler,
  API Gateway, S3, CloudFormation, SSM, Amplify, Polly). Data stays Delhi; only hosting is in Sydney.
- **Polly**: Kajal (neural) synthesises Hindi in `ap-southeast-2`.
- **Bedrock**: every model returns "Operation not allowed" (account security restriction; AWS says only
  Support can lift it). Until it is lifted, "Ask Khidki" answers from verified templates and says so.

## DOCS
- Unverified research citations get "(verify)"; no DOIs we have not confirmed.
- `docs/demo-script.md`: a 2:40 cut (problem → 6 AM plan with a Cedar-reasoned PE decision → instruction,
  tap and Step Functions verify ✓ → partial-open follow-up → real-room card if we have it → AWS console
  montage → benchmark → printable timetable and close). Ask Khidki is cut first if over time.
