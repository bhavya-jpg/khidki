# KHIDKI (खिड़की) — Complete Build Spec for Claude Code

> **"Open the window at the right minute."**
> A physics-twin + optimizer + verified-nudge system that tells a Delhi teacher *exactly when* to open or close the classroom windows on a bad-air day — so 40 children breathe less PM2.5 **and** stay below the CO₂ levels that wreck concentration.

**Hackathon:** Environmental Hacks — Event 02, Bharat Builds Tour (WeMakeDevs × AWS Builder Center)
**Dates:** Thu 8 Oct – Sun 11 Oct 2026 (online), optional build day at DTU Delhi on Sat 10 Oct
**Track:** **Air** (sub-themes hit: *School safety on bad days*, *Indoor air*, *Pollution exposure*, *AQI*)
**Build mode:** Ship It (deployed on AWS, Mumbai `ap-south-1`) **and** Build It (runs locally with AWS open-source tools, no account) — both, like the First Commit winners.

---

## 0. How to use this file

### For the human (read first)
1. **Do not create the project repo or write any project code before the hackathon clock starts on 8 Oct.** The rules say anything begun before kickoff is disqualified, and a repo whose git history doesn't match the event dates disqualifies the whole team. Planning and practice are allowed — this document *is* planning.
2. On kickoff day, create an empty public GitHub repo, put this file at `docs/SPEC.md` as the first commit (it's a plan, which is allowed — committing it openly is the honest move), then open VS Code and tell Claude Code:
   > *"Read docs/SPEC.md completely. Then execute Phase 0 → Phase 1 → … in order. After each phase, run the phase's acceptance checks, commit, and stop to show me the result before moving on."*
3. Do the **Pre-kickoff checklist (§17.1)** now — especially creating the AWS account early (new accounts can sit under a verification hold that blocks CloudFront/Bedrock for a while; the Beacon team hit exactly this).
4. Things only you can do: record the video, write the Builder Center blog, submit the form, verify student status. Budget 6+ hours on Sunday for these.

### For Claude Code (binding instructions)
- Treat **§19 Guardrails** as hard rules. If any instruction elsewhere conflicts with §19, §19 wins.
- Work **phase by phase** (§17). Never start a P1 item while any P0 item is failing. Never start P2 while P1 is failing.
- Every phase ends with: tests green → `ruff` + `mypy` clean on `core/` → commit with a descriptive message → short summary to the human.
- **Verify, don't assume:** package APIs (Strands, cedarpy, CDK constructs), model IDs, and AWS service availability in `ap-south-1` change. Before using any of them, check the installed version's docs/signatures (`python -c "import x; help(x.y)"`, `pip show`, `aws ... describe-*`). If something in this spec is out of date, adapt and note it in `docs/LEARNINGS.md`.
- Commit early and often (at least every 1–2 hours of work). The git history is evidence for the judges that the work happened during the event.
- Keep a running `docs/LEARNINGS.md` ("what fought back") — it feeds the blog post that wins the AirPods prize.

---

## 1. TL;DR

| | |
|---|---|
| **Problem** | On high-AQI days, Delhi classrooms face a trap: windows **closed** → CO₂ climbs past 1,500–2,500 ppm within a period or two (attention and decision-making drop sharply); windows **open** → outdoor PM2.5 pours in. Teachers decide by feel and temperature. A 2025 field study found CO₂ alarms reduced CO₂ ~19% but *increased* PM, and its authors called for a signal that balances air quality, ventilation **and** temperature together. Nobody gives teachers that. |
| **Who** | Ms. Sunita (fictional persona), Class 6B teacher, East Delhi government school, 44 students, 3 with asthma. Plus the principal (outdoor assembly/PE decisions, GRAP compliance) and parents. |
| **What Khidki does** | Every morning it plans the day's ventilation per classroom (5-minute resolution) using a physics digital twin + real outdoor forecast + the timetable. During the day it shows one calm instruction on a cheap tablet ("Open both sides — 4 min"), **verifies from the CO₂ curve itself whether the window really opened**, re-plans every 5 minutes, and at night reports to parents in Hindi: *"Today your child's class breathed 31% less PM2.5 than with windows shut, and spent 12 minutes above 1,500 ppm CO₂ instead of 2 h 40 m."* |
| **Why it's hard (judges love this)** | Two-pollutant, opposite-sign control problem; dynamic programming with a teacher-attention budget; system identification of each room from children's own exhaled CO₂ (tracer-gas decay method); policy-as-code safety (Cedar); verified human-in-the-loop (Step Functions callback); LLM that *explains* but never *decides*, with a number-fidelity guard. |
| **AWS** | IoT Core, Lambda, API Gateway, DynamoDB, Step Functions, EventBridge Scheduler, Bedrock (Nova 2 Lite via global inference profile), Polly (Kajal, Hindi neural), S3, CloudWatch, Amplify Hosting, (P1) Cognito, AppSync Events. AWS open source: **Strands Agents SDK**, **Cedar**, **Powertools for AWS Lambda**, **AWS IoT Device SDK**, moto/LocalStack for local mode. IaC with **AWS CDK**. |
| **Design** | "The window is the interface." A data-true `AirWindow` (every dot = a fixed amount of real PM2.5; CO₂ as a warm breath haze; panes really open) is the one signature element, used on a scroll-scrubbed landing page, a calm teacher tablet, a principal's school-facade view and a five-windows policy Lab. Palette lifted from the classroom (blackboard, whitewash, Delhi smog, turmeric), Anek Latin + Devanagari with the width axis as meaning. Patterns borrowed from Awwwards Sites of the Year and the NYT air-pollution piece (§14). |
| **Proof** | A benchmark harness replays real Delhi outdoor PM2.5 (CAMS via Open-Meteo, Oct–Dec 2025 school days) through the twin under 5 policies (always closed, always open, CO₂-alarm, temperature-driven teacher, Khidki) and reports PM dose vs CO₂-minutes on a Pareto chart. |

---

## 2. The hackathon — facts and hard rules (verified from the official pages, 3 Oct 2026)

Sources: <https://www.wemakedevs.org/aws/env>, `/aws/env/rules`, `/aws/env/schedule`, `/aws/rules`.

### 2.1 Format
- Online Thu 8 – Sun 11 Oct 2026, anywhere in India; optional in-person build day at **DTU Delhi, Sat 10 Oct, 8 AM–8 PM** (workshops, project feedback, Amazon team). Attending in person gives **no** scoring advantage.
- Teams of 1–4. University students in India, 18+. Each member registers separately; needs a WeMakeDevs account + **AWS Builder Center profile with student status verified**.
- Exact kickoff time and submission deadline time were "being finalised" on the schedule page as of 3 Oct — **check `/aws/env/schedule` daily; plan to submit by 2 PM IST Sunday.**

### 2.2 Tracks and prizes
- Three tracks, each judged separately: **Air** · Heat and Water · Waste and Energy. Each track winner: ₹2,00,000 + $2,000 AWS credits.
- 4 runners-up across all tracks: $1,000 AWS credits each.
- **Top 5 blogs** (published on AWS Builder Center, linked in submission): AirPods.
- **Fast-track Amazon interview:** up to 10 students from top projects, picked across all tracks, for 2027/2028 graduates (6-month internship or full-time). Decided separately from prizes.

### 2.3 Judging criteria (verbatim headings, paraphrased content)
1. **Idea and Impact** — does it fix a real environmental problem, and what changes for the people living with it? *A small problem solved well beats a big one solved vaguely.*
2. **Built on AWS** — AWS open-source tool(s) locally or AWS services deployed. **Mandatory to win a prize.**
3. **Design and usability** — could someone not on your team pick it up and know what to do? Built for where its users are.
4. **The execution** — does it work? One working feature beats five that almost do.
5. **The demo video** — 3 minutes, recorded; what it does, who it's for, where AWS fits. No live demo — the video is what judges see.

### 2.4 Submission (all three required)
1. **Public repository.**
2. **Demo video on YouTube, under 3 minutes**, public or unlisted, link tested in a signed-out browser.
3. **Short writeup**: problem, the build, where AWS fits. **List the AI coding tools used** (Claude Code — say so).
- Plus (optional, for the blog prize): Builder Center blog post linked in the submission.

### 2.5 Hard rules → compliance checklist
| Rule | How Khidki complies |
|---|---|
| Build only after the clock starts; old projects don't count | Repo created on 8 Oct; first commit = this plan; all code after. |
| Repo history must match event dates | Frequent, descriptive commits throughout Thu–Sun. No squashing into one commit. |
| Must use AWS **and the demo video must show it** | Video shows IoT Core MQTT client, Step Functions execution graph, DynamoDB items, CloudWatch dashboard, Bedrock agent trace. (§21) |
| Open-source libraries/APIs/templates allowed; judged on what you added | Use libraries freely; credit them in README with licences. |
| Credit anything you didn't write, with a licence that allows use | `docs/CREDITS.md`: Open-Meteo/CAMS attribution, data.gov.in (GODL-India), libraries. |
| List AI coding tools | Writeup + README "Built with" section: Claude Code. |
| Features only in the writeup don't count | Everything claimed is shown in the video. |
| Feasibility on Free Tier | Whole stack runs on pennies/day (§11.5). |

---

## 3. What won last time — First Commit (Event 01, 17–20 Sep 2026)

Same organisers, same AWS partnership, same judging style. These are the single best predictors of what this panel rewards. Source: <https://www.wemakedevs.org/aws/first-commit/projects> and the winners' public READMEs.

| Prize | Project | What it was | Why it won (pattern) |
|---|---|---|---|
| **1st – Ship It** | **Suraksha** — agentic companion for an aging parent | Galaxy Watch + tablet voice companion; Bedrock Nova 2 Lite agents; Cedar "consent guard" before every tool call; Step Functions family-escalation chain with `waitForTaskToken`; EventBridge proactive sweeps; DynamoDB single-table memory; Transcribe/Polly in Hindi/Hinglish; CDK; Amplify | Named persona ("Amma, 72, Bengaluru"). **"The model decides language and judgement; code decides actions."** "Quiet by design — most days it says nothing." Policy-as-code. Human-in-the-loop with real callbacks. ~15 AWS services, each with a reason. Honest labelling of simulated history. |
| **2nd – Build It** | **Beacon Night Shift** — on-call agent that fixes the 3 AM page by voice | Strands agent on Nova 2 Lite; allowlisted fixes; dry runs; **"recovered means proven"** (refuses to say fixed until CloudWatch agrees); consent checked against the user's actual transcript, not the model's claim; Step Functions verify loop; runs fully locally against moto; 244 tests; Builder Center blog | Safety model in code + IAM, not prompts. **Verification of outcomes.** Local mode with no AWS account. Tests as spec. Production notes. A crisp one-sentence story. |
| **3rd – Best UI** | **CampusEvac** — two-player fire-evacuation drill | 3D first-person evacuee + overhead warden; AppSync Events realtime; DynamoDB event log; Polly narration with caching; SES reports; CDK; Amplify | Trains a neglected role (the warden). Real-time multi-view UX. Server recomputes scores rather than trusting the client. |
| Runners-up | Magpie (finance workspace), FreshTrace, Expressive captions, Factcade (factory ops copilot) | — | Deployed, polished, specific users. |
| Top blogs | Slate, KavachPay, Career Agent, VaporTrace, Clusterbreak | Builder Center posts about *what fought back* | Concrete engineering stories with specific failure → fix narratives. |

### 3.1 The winning pattern (Khidki is designed to hit every point)
1. **One named human, one vivid moment.** ("It's 3 AM, payments are failing." / "Amma wears the watch.") → *"It's 10:05, period 3, CO₂ is 2,100 ppm and the AQI outside is 380."*
2. **Agentic AI, but code decides.** LLM for language and explanation; deterministic code + policy for actions.
3. **Policy-as-code safety (Cedar).** Both top-2 used it or equivalent allowlists.
4. **Human-in-the-loop with real callbacks** (Step Functions `waitForTaskToken`).
5. **Proven outcomes**, not claimed ones (Beacon's CloudWatch verification ≈ Khidki's CO₂-decay verification).
6. **Deep, justified AWS** (10–15 services, each with a role) + **CDK** IaC + live URL.
7. **Local mode** that runs without an AWS account (covers "Build It" judges too).
8. **Restraint as a feature** ("quiet by design") — Khidki caps teacher interruptions per day.
9. **Hindi-first** voice/text for real Indian users.
10. **Engineering hygiene:** tests, safety doc, architecture diagram, runbook, honest limitations, blog.

---

## 4. Similar hackathons — what tends to win environmental/air tracks

- **AWS/Tech To The Rescue Air Quality Hackathon (Dec 2023):** winners closed specific *information gaps* for specific organisations (e.g., a platform integrating live sensor data for an advocacy network; a visual that showed lung damage for a location's AQI). Lesson: specific user + specific gap.
- **University of Utah × AWS AI air-quality hackathon:** 1st place predicted AQI and texted users a *personalised* risk score that considered their health. Lesson: personalised, actionable output beats raw data.
- **ASDI / AWS re:Invent Code Green:** winners used open datasets (OpenAQ) to visualise PM2.5 for cities. Lesson: these were early-era wins; **in 2026 a dashboard is table stakes and will not win.**
- **What loses (from judge criteria + experience):** generic AQI dashboards, chatbots that restate AQI, "safe route" planners without data, ML classifiers with no user, anything whose demo is mostly slides.

**Prediction for this event's Air track (Delhi host, October = GRAP season starting):** a flood of AQI dashboards/alerts, stubble-burning fire maps (NASA FIRMS), "AI pollution chatbots", and route planners. **Khidki is deliberately orthogonal**: indoor, school-specific, physics-grounded, measurable, and verified.

---

## 5. Why Khidki — problem, evidence, alternatives

### 5.1 The problem in numbers
- Delhi has **5,556 schools and ~44.9 lakh students** (UDISE+ 2024-25), **2,681 government schools**. Most classrooms are naturally ventilated.
- GRAP stages (CAQM): I Poor (AQI 201–300), II Very Poor (301–400), III Severe (401–450), IV Severe+ (>450). Under the revised GRAP (Dec 2024) schools shift to hybrid for Class ≤V at Stage III and Classes VI–IX & XI at Stage IV — **every other bad day, children are physically in class breathing whatever the window lets in.**
- Delhi PM2.5 has a strong daily cycle in post-monsoon/winter: high overnight/early morning under a shallow boundary layer, lower in the afternoon when mixing deepens — school hours sit on the bad side of that curve. *That timing structure is exactly what an optimizer can exploit.*
- **CO₂ and cognition:** in the Harvard COGfx double-blind study (Allen et al., 2016, EHP), cognitive scores were ~15% lower at ~945 ppm and ~50% lower at ~1,400 ppm vs ~550 ppm. (Caveat to state honestly in docs: other studies found task-dependent effects. Khidki treats CO₂ as a ventilation/stuffiness indicator with a cognition-motivated penalty, not a medical claim.)
- A field study of five Delhi-area schools found naturally ventilated classrooms keep windows closed in winter for warmth, and even small ventilation cuts produce CO₂ exceedance hours (REHVA Journal).

### 5.2 The evidence gap Khidki fills
Rawat et al. (2025, *Science of the Total Environment*, 179543) fitted classrooms with an IoT CO₂ display that alerted teachers at 1,000/1,500 ppm:
- Visual alarms cut CO₂ by **~19.5%**, visual-acoustic by ~19%.
- **But PM concentrations increased** because of window opening.
- **Teachers' decisions were driven mainly by classroom temperature.**
- Visual alarms were preferred (less distracting than sounds).
- The authors recommend a **holistic signal integrating temperature, air quality and ventilation**, and a **school-level ventilation protocol**.

Rawat & Kumar (2024, *J. Building Engineering*, 108813): **scheduled ventilation (windows opened during non-occupancy) + air purifier during occupancy** gave the best results — up to 36% / 14% / 28% reductions in PM10 / PM2.5 / CO₂.

> **Khidki = the holistic, school-level, scheduled-ventilation signal those papers call for, made dynamic with Delhi's live forecast and verified with sensors.** Quote this framing (paraphrased) in the README, video and blog.

### 5.3 Alternatives considered and rejected (keep in docs to show judges rigour)
| Idea | Why not |
|---|---|
| AQI dashboard / alerts / chatbot | Saturated; restates data people already have. |
| Stubble-smoke trajectory attribution (FIRMS fires + winds) | High wow, but attribution science is contestable in 4 days; unclear end user; many teams will map FIRMS fires. |
| Outdoor-worker heat stress (WBGT work-rest) | Strong science, but off-season in October and a different track. |
| Informal e-waste EPR traceability (Seelampur) | Very niche, but needs partners to look real; demo is dry. |
| Monsoon underpass/basement flood warning | Off-season; needs drainage data that isn't open. |
| **Khidki** | In-season (GRAP season starts in Oct), Delhi-specific, works end-to-end without partners, outcome is measurable, published evidence gap, deep AWS fit, great video moments. ✅ |

---

## 6. Product

### 6.1 Personas (fictional — label them as such everywhere)
- **Sunita Sharma, 41 — Class 6B teacher**, "Demo Sarvodaya Vidyalaya, East Delhi" (fictional school near Anand Vihar). 44 students aged ~11. Room ≈ 8.0 × 6.5 × 3.2 m (166 m³). Three road-side windows, two corridor-side windows, no purifier. Uses a shared ₹8–10k Android tablet. Hindi-first. Has 30 seconds of attention to spare per period.
- **Mr. R. K. Verma, 55 — Principal.** Decides outdoor assembly/PE; must follow DoE/CAQM circulars; reports to the School Management Committee.
- **Meena, 34 — parent of Ananya (asthma).** Wants to know: "was today okay in her classroom?" Reads Hindi on WhatsApp-style links.
- **(Secondary) Class 3A teacher** — room *with* a purifier, to show the optimizer behaving differently.

### 6.2 Core user journeys
1. **06:00 — Morning plan.** Khidki pulls the outdoor forecast, bias-corrects it with the nearest CPCB station, computes an indicative GRAP stage, plans every room's day, decides outdoor assembly/PE per school policy, and posts a one-screen Hindi brief to the principal (with Polly audio).
2. **During class — calm instruction.** Teacher tablet shows one big card. Most periods: *"Band rakhiye — sab theek hai"* (keep closed — all fine). When action is due: *"Dono taraf ki khidkiyan kholiye — 4 minute"* with a countdown, a "Why?" line, and two buttons that name what happened: **खोल दीं / I've opened them** and **अभी नहीं हो सकता / Can't right now** (reasons: too cold, too noisy, raining, exam on).
3. **Verification.** Three (sim-)minutes later Khidki checks the CO₂ curve. ✓ *"Hawa badal gayi — CO₂ gir raha hai."* Or: teacher tapped "I've opened them" but the curve barely moved → *"Lagta hai ek hi taraf khuli hai — corridor wali khidki bhi kholiye."* (the demo's "aha" moment).
4. **Re-planning.** Every 5 minutes, or immediately after a "Can't" or a forecast deviation, the plan re-optimizes from the measured state.
5. **Ask Khidki (agent).** Teacher/principal asks by text (P1) or voice (P2): *"Kya main 11:20 pe PT ke liye bachchon ko bahar le jaun?"* → the agent calls tools (forecast, policy check, twin simulation) and answers with numbers and the policy reason.
6. **16:30 — Day report.** Per room: PM2.5 dose vs baselines, minutes above 1,000 / 1,500 ppm, nudges issued/verified, teacher-attention used. Parent digest (Hindi/English, class-level only).
7. **Nightly — Room fingerprint.** Fits each room's air-change rates per window state, PM penetration and deposition from the day's data; tomorrow's plan uses the updated twin.

### 6.3 Surfaces
| Route | Who | Purpose |
|---|---|---|
| `/` | Everyone/judges | Landing: problem in one screen, live room tile, "how it works" diagram, links to Lab and Demo. |
| `/teacher/:roomId` | Teacher (tablet) | One calm decision beside a live `AirWindow`, mini charts, "I've opened them" / "Can't right now". |
| `/school/:schoolId` | Principal | Room grid (live), outdoor forecast curve, indicative GRAP banner + DoE/CAQM reminder, today's activity decisions with policy reasons, override (logged), day/week reports. |
| `/parent/:token` | Parent | Class-level daily digest + Polly audio. No child PII. |
| `/lab` | Judges, curious users | **Twin playground**: set room size, students, windows, purifier, date (from real replay days), profile → see Khidki plan vs 4 baselines + Pareto chart. Plus benchmark results table. |
| `/how` | Transparency | The equations, parameters, policies (rendered Cedar), data sources, limitations. |
| `/demo` (auth) | Presenter | Sim controls: scenario, speed (1×/10×/30×), inject events (teacher ignores, partial opening, forecast spike). |

### 6.4 Design principles (full system in §14)
- **The window is the interface** — every screen is seen through a drawn classroom window whose contents are the real air.
- **Quiet by design.** Visual-first (the Surrey study found visual alerts less distracting); one orchestrated moment per screen; optional chime and Polly voice.
- **Attention budget.** Max **6 window changes per room per day** (configurable). The optimizer respects it (§8.1).
- **Never alarmist.** Sindoor red only for "outdoor air severe — keep children inside".
- **Hindi-first, bilingual.** Anek Devanagari + Anek Latin.
- **Colour is never the only signal** (icon + verb + colour).
- **Works on a cheap tablet** at 1024×600, touch targets ≥ 64 px, survives flaky Wi-Fi.
- **Honest:** simulated-data badge, demo-speed badge, outdoor data attributed, particle legend on every window.

---

## 7. The science (implement in `core/` as pure, typed, tested Python — no AWS imports)

### 7.1 Well-mixed classroom box model
State per room: indoor CO₂ `C` (ppm) and indoor PM2.5 `P` (µg/m³). Control `u = (w, a)` where window state `w ∈ {CLOSED, CRACKED, OPEN}` and purifier `a ∈ {OFF, ON}` (only if the room has one).

```
dC/dt = λ(w)·(C_out − C) + S_co2
dP/dt = p(w)·λ(w)·P_out − (λ(w) + k + q(a)/V)·P + E/V
```
| Symbol | Meaning | Default (configurable per room; overwritten by fingerprint) |
|---|---|---|
| `λ(w)` | air changes per hour by window state | CLOSED 0.7 h⁻¹ · CRACKED 2.5 h⁻¹ · OPEN 6.0 h⁻¹ (cross-vent both sides: 10 h⁻¹) |
| `C_out` | outdoor CO₂ | 450 ppm (or Open-Meteo `carbon_dioxide`) |
| `S_co2` | CO₂ source, ppm/h = `N·G·3.6e6 / V` | `G` = 0.0035 L/s per seated 10–13 y/o, 0.0052 L/s per adult (approximate, after Persily & de Jonge 2017, *Indoor Air* 27:868) |
| `V` | room volume m³ | 166 |
| `N` | occupants (from timetable; 0 in recess if class goes out) | 44 + 1 teacher |
| `p(w)` | PM2.5 penetration factor | CLOSED 0.8 · CRACKED 0.95 · OPEN 1.0 |
| `k` | PM2.5 deposition loss rate | 0.2 h⁻¹ (literature for homes ~0.08–0.10; classrooms higher with occupancy/resuspension) |
| `q(a)` | purifier effective CADR m³/h | ON: 350 × 0.8 effectiveness; OFF: 0 |
| `E` | indoor PM2.5 source µg/h | 0 default (option for chalk/resuspension) |

Sanity numbers (put these in `tests/test_physics.py` as regression checks): with N=45, V=166, closed λ=0.7 → `S_co2 ≈ 3,400 ppm/h`, steady state ≈ 5,300 ppm, after one 40-min period from 600 ppm ≈ 2,300 ppm. Open λ=6 → steady state ≈ 1,000 ppm. Outdoor 250 µg/m³, closed → indoor SS ≈ 155; open → ≈ 242; closed + purifier → ≈ 54. **This is the dilemma, in numbers.**

**Exact discretisation** (use this, not Euler): over a step `Δt` with constant `u` and inputs, for `dx/dt = b − a·x`:
`x(t+Δt) = b/a + (x − b/a)·exp(−a·Δt)`. CO₂: `a = λ`, `b = λ·C_out + S`. PM: `a = λ + k + q/V`, `b = p·λ·P_out + E/V`. Handle `a → 0` safely.

Step size: **Δt = 5 min** for planning, 30 s for the simulator.

### 7.2 Exposure and cost metrics (`core/dose.py`)
- **PM2.5 inhaled dose per child** (µg) = Σ `P(t)·IR·Δt` while the child is in the room. `IR` default 0.5 m³/h (seated/light activity, child; configurable; cite US EPA *Exposure Factors Handbook* ch. 6). Headline claims use **relative %**, which is insensitive to IR.
- **CO₂ minutes** above 1,000 and 1,500 ppm while occupied.
- **CO₂ discomfort points** (piecewise linear per occupied minute): 0 below 1,000; rises to 1 at 1,500; to 4 at 2,000; +10 per additional 1,000 ppm.
- **Cold exposure** (thermal proxy): open-fraction × max(0, 18 °C − T_out) per minute (T_out from Open-Meteo `temperature_2m`). Open-fraction: CLOSED 0, CRACKED 0.3, OPEN 1.
- **Teacher attention used:** number of window-state changes requested.

### 7.3 Indian AQI and GRAP (`core/aqi.py`, `core/grap.py`)
- Implement CPCB National AQI PM2.5 sub-index (24-h breakpoints): Good 0–30 → 0–50; Satisfactory 31–60 → 51–100; Moderate 61–90 → 101–200; Poor 91–120 → 201–300; Very Poor 121–250 → 301–400; Severe 250+ → 401–500. Linear interpolation. Tests: 45 µg/m³ → 75; 150 µg/m³ → ~323.
- **Indicative GRAP stage** from city AQI: I (201–300), II (301–400), III (401–450), IV (>450). Label it "indicative" — the *official* stage is whatever CAQM has ordered; the principal can set the official stage in the UI. Show the matching school measure as a reminder (Stage III: hybrid up to Class V; Stage IV: hybrid VI–IX & XI per revised GRAP, Dec 2024) with a link to the DoE circulars page; **never auto-enforce or contradict an official order**.

### 7.4 Outdoor data and bias correction (`data/`)
- **Forecast:** Open-Meteo Air Quality API (CAMS), keyless for non-commercial use.
  `GET https://air-quality-api.open-meteo.com/v1/air-quality?latitude=28.6469&longitude=77.3152&hourly=pm2_5,pm10,us_aqi,carbon_dioxide&timezone=Asia/Kolkata&forecast_days=2&past_days=1`
  Also weather: `https://api.open-meteo.com/v1/forecast?...&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation`.
  **Attribution required** (CAMS ENSEMBLE + Open-Meteo) — show in footer and `/how`.
  Note CAMS global is ~45 km resolution and often under-predicts Delhi peaks → bias-correct.
- **Nowcast:** CPCB real-time AQI via data.gov.in resource `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`:
  `GET https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69?api-key=$DATAGOV_KEY&format=json&limit=500&filters[city]=Delhi`
  The public sample key returns only a handful of records — register for a personal key (free) and store it in SSM Parameter Store / Secrets Manager. **On Day 1, inspect a real payload and document the fields** (station, lat/lon, pollutant_id, pollutant_avg/min/max, last_update) and whether `pollutant_avg` is a concentration or sub-index; write that in `docs/LEARNINGS.md`. Pick nearest station by haversine (default: Anand Vihar for the demo school).
- **Bias correction (simple MOS):** `r = median(obs/forecast)` over the last 6 h of matched hours, clipped to [0.5, 4]; corrected forecast `F'(h) = F(h)·(1 + (r − 1)·exp(−h/12))` for lead time h hours. Unit-test it. If CPCB is unavailable, `r = 1` and flag "uncorrected".
- **Replay days (benchmark + demo):** Open-Meteo supports `start_date`/`end_date` for CAMS global from Aug 2022. Cache Delhi school days **15 Oct – 20 Dec 2025** into `data/fixtures/replay/*.json` (with attribution file). Optional P2: OpenAQ v3 (needs API key) for station truth to calibrate a fixed replay scale factor; otherwise document the uncorrected limitation.
- **Caching & resilience:** cache every fetch in S3/DynamoDB with timestamp; if a source fails, use last good data and show "data delayed (xx min)".

---

## 8. The brain — optimizer, calibration, verification

### 8.1 Optimizer (`core/optimizer.py`) — finite-horizon dynamic programming
- Horizon: from now to end of school day, Δt = 5 min (≤ ~80 steps).
- State grid: CO₂ 400–4,000 ppm in 25-ppm bins; PM 0–400 µg/m³ in 2-µg bins; previous window state (3). Use bilinear interpolation of the value function. Vectorise with NumPy (no SciPy needed — keeps Lambda package small).
- Actions: window {CLOSED, CRACKED, OPEN} × purifier {OFF, ON} (purifier only if present).
- **Stage cost** (normalised per day so weights are intuitive):
  `J = α·PMdose/PMdose_ALWAYS_OPEN + (1−α)·CO2pts/CO2pts_ALWAYS_CLOSED + β·cold/cold_ALWAYS_OPEN + μ·[window changed]`
  - Profiles: **Balanced** α=0.5, **Lungs-first** (sensitive students present / Severe days) α=0.7, **Focus-first** (exam day) α=0.35. β default 0.3.
  - Baseline normalisers come from simulating the two trivial policies first (cheap).
- **Attention budget via Lagrangian:** find the smallest switch penalty μ ≥ 0 such that the plan uses ≤ `max_changes` (default 6) window changes; bisection on μ (≤ 8 DP solves). Document this trick in the blog — it's elegant.
- **Policy mask:** before solving, query Cedar (§9) for every (time step, action, CO₂ band) and forbid disallowed actions. CO₂ bands: 0 <800, 1 <1,000, 2 <1,500, 3 <2,000, 4 ≥2,000. Batch the checks (`is_authorized_batch` if available).
- **Fixed constraints:** "Can't" reasons from the teacher become constraints for the rest of the period/day (cold → β×2 for that room today; exam → freeze window state for that period; noise → OPEN replaced by CRACKED corridor-side; rain → no OPEN for 30 min).
- **Output:** `Plan { room_id, date, version, profile, steps: [{t, window, purifier, predicted_co2, predicted_pm, reason_code}], instructions: [{t_start, t_end, action, duration_min, reason_code}], kpis_predicted, baselines_predicted }`. `instructions` collapses steps into human actions ("open both sides for 4 min at 10:10").
- **Reason codes** (used by UI and agent, never free text from the LLM): `CO2_RISING_FAST`, `OUTDOOR_PM_LOW_WINDOW`, `RECESS_PURGE`, `OUTDOOR_PM_SPIKE_CLOSE`, `PURIFIER_DURING_CLOSED`, `COLD_LIMIT`, `POLICY_FORBIDS_OPEN`, `ATTENTION_BUDGET`, `KEEP_STEADY`.
- **Performance target:** full re-plan < 3 s in Lambda at 1,769 MB; < 10 s worst case with bisection. Profile and coarsen grid if needed.
- **Receding horizon:** replan every 5 (sim) minutes from the latest **state estimate** (§8.2).

### 8.2 State estimation and window inference (`core/inference.py`)
- **State estimate:** complementary filter — blend model prediction with sensor reading (`x̂ = x_pred + K·(z − x_pred)`, K≈0.6 for CO₂, 0.4 for PM). With no sensors (Tier 0), run open-loop on the model.
- **Implied air-change rate** from CO₂ over a sliding 3–5 min window: least-squares fit of `dC/dt = λ(C_out − C) + S` for λ (occupied), or of `ln(C − C_out)` slope (unoccupied decay). Classify to the nearest fingerprint λ for CLOSED/CRACKED/OPEN with hysteresis and a confidence score.
- This gives **"Khidki knows the window opened without a sensor on the window"** — a key demo moment. Reed-switch data (if present) overrides.

### 8.3 Room fingerprint — system identification (`core/calibration.py`)
- Nightly (and on demand), fit per room from the day's telemetry:
  1. `λ_CLOSED`, `λ_CRACKED`, `λ_OPEN` from CO₂ decay segments (empty room after school / recess) using the tracer-gas decay method (ASTM E741 concept; the tracer is the children's own exhaled CO₂), and from occupied segments using the known source `S`.
  2. With λ fixed, fit `p` and `k` (and purifier effectiveness) for PM by small grid search minimising squared error.
- Report fit quality (R², residual RMSE), number of segments used, and **only accept** parameters within physical bounds (λ 0.1–20 h⁻¹, p 0.3–1.0, k 0.02–1.5 h⁻¹); otherwise keep yesterday's and flag.
- Acceptance test: from simulated data with known parameters + noise, recover λ within ±10% and p, k within ±20%.

### 8.4 Verification loop (Step Functions `NudgeSM`)
```
IssueNudge (Lambda, .waitForTaskToken, timeout = 3 sim-min)
   ├─ teacher taps the confirm button ("I've opened them") → SendTaskSuccess {result:"done"}
   ├─ teacher taps Can't → SendTaskSuccess {result:"cant", reason}
   └─ timeout            → {result:"no_ack"}
→ Choice
   ├─ "cant" → RecordConstraint → TriggerReplan → End(NOT_POSSIBLE)
   └─ else  → Wait (3 sim-min) → VerifyFromSensors (Lambda: implied λ vs expected)
        → Choice
           ├─ match                         → VERIFIED (or VERIFIED_SILENT if no_ack)
           ├─ done but mismatch, attempt 1  → FollowUpNudge ("other side too?") → loop once
           ├─ no_ack and mismatch, attempt 1 → GentleRenudge → loop once
           └─ otherwise                     → NOT_FOLLOWED → TriggerReplan
```
- Wait durations = sim-seconds ÷ speed (from `SimClock`, §15).
- Every outcome is written to DynamoDB and counted in CloudWatch EMF metrics (`NudgesIssued`, `NudgesVerified`, `NudgesPartial`, `NudgesNotFollowed`).
- **Tone rule:** NOT_FOLLOWED is never shown as blame; it just re-plans.

### 8.5 Baselines and the benchmark (`core/baselines.py`, `bench/`)
Policies to simulate on the same twin and outdoor series:
1. `ALWAYS_CLOSED`
2. `ALWAYS_OPEN`
3. `CO2_ALARM` — SAVE-style: open when CO₂ > 1,500, close when < 1,000; 2-min reaction delay; 70% compliance (seeded RNG)
4. `TEMPERATURE_TEACHER` — open if T_out ≥ 22 °C else closed (the behaviour the Surrey study observed)
5. `KHIDKI` — the optimizer (with the same 70% compliance for fairness, plus a 100%-compliance upper bound)

Run over every cached replay day × 2 room types (no purifier / purifier). Output `bench/results/summary.csv` + `bench/results/pareto.png` + Markdown table in `docs/benchmark.md`:
mean PM2.5 dose reduction vs ALWAYS_OPEN, CO₂ minutes >1,500, cold minutes, window changes, and **"days on which Khidki Pareto-dominates CO2_ALARM"**.
**Honesty rule:** all results are labelled *"simulation on a modelled classroom driven by real outdoor data; not a field trial."* If Khidki doesn't dominate on some days, report it and explain (that candour scores points).

### 8.6 Tiers (adoption story)
- **Tier 0 — no hardware:** plan from forecast + room geometry + timetable (open loop). Every classroom in Delhi could use this tomorrow.
- **Tier 1 — CO₂ sensor only:** enables verification and fingerprinting (cheapest useful sensor).
- **Tier 2 — CO₂ + PM2.5 sensor:** full closed loop.

---

## 9. Policy as code — Cedar (`core/policy/`)

Use `cedarpy` (Python bindings to the Rust Cedar engine; Cedar is an AWS open-source project). Validate policies against the schema at build time (`validate_policies`) and in CI.

### 9.1 Schema sketch (`khidki.cedarschema`) — adapt syntax to the installed Cedar version
```cedar
namespace Khidki {
  entity School = { name: String };
  entity Room in [School] = { grade: Long, sensitiveCount: Long, hasPurifier: Bool };
  entity User in [School, Room] = { role: String };            // "teacher" | "principal" | "parent" | "admin"
  entity Activity in [School] = { kind: String };              // "assembly" | "pe" | "recess_outdoor"

  type VentCtx = { outdoorPm25: Long, co2Band: Long, grapStage: Long, minuteOfDay: Long, tempOutC: Long };
  type ActCtx  = { maxPm25During: Long, grapStage: Long, minGrade: Long };

  action "ventilate.open", "ventilate.crack", "ventilate.close"
    appliesTo { principal: [Room], resource: [Room], context: VentCtx };
  action "activity.outdoor"
    appliesTo { principal: [School], resource: [Activity], context: ActCtx };
  action "view.room", "view.school", "plan.override", "grap.setOfficial"
    appliesTo { principal: [User], resource: [Room, School] };
}
```

### 9.2 Safety and school policies (`policies/*.cedar`) — starting set
```cedar
// S1: never open fully into Severe outdoor air unless CO2 is critical (≥2000 ppm band)
forbid (principal, action == Khidki::Action::"ventilate.open", resource)
when { context.outdoorPm25 > 250 && context.co2Band < 4 };

// S2: outdoor activities blocked when forecast PM2.5 during the activity exceeds CPCB 'Poor' (school policy, configurable)
forbid (principal, action == Khidki::Action::"activity.outdoor", resource)
when { context.maxPm25During > 90 };

// S3: stricter for primary classes
forbid (principal, action == Khidki::Action::"activity.outdoor", resource)
when { context.minGrade <= 5 && context.maxPm25During > 60 };

// S4: no outdoor activities at indicative/official GRAP stage III or above
forbid (principal, action == Khidki::Action::"activity.outdoor", resource)
when { context.grapStage >= 3 };

// defaults
permit (principal, action in [Khidki::Action::"ventilate.open", Khidki::Action::"ventilate.crack", Khidki::Action::"ventilate.close"], resource);
permit (principal, action == Khidki::Action::"activity.outdoor", resource);

// Access control
permit (principal, action == Khidki::Action::"view.room", resource) when { principal in resource };          // teacher/parent of that room
permit (principal, action in [Khidki::Action::"view.school", Khidki::Action::"view.room", Khidki::Action::"plan.override", Khidki::Action::"grap.setOfficial"], resource)
when { principal.role == "principal" && resource in principal };   // adapt: principal is `in` their School
forbid (principal, action == Khidki::Action::"plan.override", resource) unless { principal.role == "principal" };
```
- Every decision Khidki makes stores the **policy IDs that fired** (`determining_policies`/diagnostics) so the UI and agent can say *"PE moved indoors because policy S2: forecast PM2.5 in that hour is 142 µg/m³ (> 90)."*
- Principal overrides are permitted, **logged with who/when/why**, and visible on the school page.
- Tests: table-driven cases for each policy + "safety cannot be disabled by a teacher" + schema validation.

---

## 10. The agent — Strands Agents SDK on Amazon Bedrock

### 10.1 Setup
- `pip install strands-agents strands-agents-tools` (Python ≥ 3.10). Verify the current import path for the Bedrock model class in the installed version (historically `from strands.models import BedrockModel`).
- Model: **Amazon Nova 2 Lite** via the **global cross-region inference profile** `global.amazon.nova-2-lite-v1:0`, called from `ap-south-1` (Mumbai supports Nova 2 Lite only through the global profile). Confirm access in the Bedrock console during pre-kickoff; IAM must allow `bedrock:InvokeModel*` on the inference profile and destination regions.
- Temperature low (0.2). Max tokens modest (600).

### 10.2 Tools (all deterministic, all return JSON with numbers)
| Tool | Returns |
|---|---|
| `get_room_now(room_id)` | latest CO₂, PM, temp, inferred window state + confidence, current instruction, next instruction |
| `get_outdoor_forecast(school_id, hours)` | bias-corrected hourly PM2.5, temp, indicative GRAP, data freshness |
| `simulate_option(room_id, option)` | runs the twin for a what-if (e.g., "keep closed until 11:00", "take class outside 11:20–12:00") → predicted CO₂/PM/dose deltas |
| `check_policy(action, context)` | Cedar decision + determining policy IDs + human-readable policy text |
| `get_plan(room_id)` | today's instructions with reason codes |
| `get_day_report(room_id, date)` | KPIs vs baselines |
| `explain_reason_code(code)` | fixed bilingual explanation strings |

### 10.3 Agent rules (system prompt + code guards)
- **The agent never changes the plan or actuates anything.** It can only *read* and *simulate*. Plan changes go through the API with a human tap (Cedar-checked).
- Answer in the user's language (Hindi/Hinglish/English), ≤ 80 words for teachers, cite the numbers it used.
- **Number-fidelity guard (`agent/guard.py`):** extract every number from the LLM's answer; each must match (±1 in last digit after rounding) a number present in the tool outputs of that turn, or be a time/date from them. If any number fails → discard the LLM text and return a **deterministic template answer** built from the tool JSON. Log the event. Unit-test with adversarial cases.
- If Bedrock errors or times out (8 s) → return the template answer with a small "assistant offline" note. **The core product never depends on the LLM.**
- Morning brief and parent digest: the LLM only **rephrases** a structured JSON into warm Hindi/English; same number-fidelity guard; template fallback always available.

### 10.4 Voice
- **Polly**: voice **Kajal** (neural, bilingual en-IN/hi-IN), `LanguageCode=hi-IN` for Hindi. Verify neural availability in `ap-south-1` with `aws polly describe-voices --engine neural --language-code hi-IN`; else call Polly in `us-east-1`. Cache MP3s in S3 keyed by SHA-256 of (text, voice, lang); pre-synthesize the ~30 fixed instruction phrases at deploy time.
- **P2:** Amazon Transcribe streaming for Hindi voice questions (verify `hi-IN` streaming support first); P1 fallback = text input.

---

## 11. Architecture on AWS

### 11.1 Diagram (put a rendered version at `docs/architecture.png` and Mermaid in `docs/architecture.md`)
```
 Classroom sensor node (real ESP32 or simulator)
        │ MQTT (X.509) khidki/{school}/{room}/telemetry
        ▼
 AWS IoT Core ──(Topic Rule)──► Lambda: ingest ──► DynamoDB (single table)
                                   │                    ▲
                                   ├─► EMF metrics ─► CloudWatch dashboard + alarms
                                   └─► deviation? ──► Lambda: replanner
                                                          │
 EventBridge Scheduler                                    ▼
   06:00 IST ─► Step Functions DailyPlanSM ─► [fetch Open-Meteo + CPCB] → [bias-correct]
                                               → Map(rooms){ optimize (Cedar-masked DP) }
                                               → activity decisions (Cedar)
                                               → brief (Bedrock Nova 2 Lite, guarded) → Polly → S3
                                               → publish (DynamoDB + realtime)
   every 5 min (07:00–14:30) ─► Lambda: replanner
   16:30 IST ─► Step Functions NightlySM ─► fingerprint fit → day reports & baselines → parent digest

 Plan instruction due ─► Step Functions NudgeSM (waitForTaskToken) ─► verify from CO₂ curve ─► outcome

 Web (Vite+React on Amplify Hosting) ──► API Gateway HTTP API ──► Lambda: api (Powertools router)
                                                            └──► Lambda: agent (Strands + Bedrock)
     ▲ realtime: AppSync Events channel /rooms/{id} (P1; P0 = 5 s polling)
 Auth: P0 demo passcodes + Cedar authz · P1 Cognito user pool (groups: teacher/principal/parent)
 Secrets: SSM Parameter Store / Secrets Manager (data.gov.in key, passcodes)
 IaC: AWS CDK (Python) · Region: ap-south-1 · Observability: CloudWatch logs (JSON), metrics, X-Ray (Powertools tracer)
```

### 11.2 Services and why each exists (paste into README "Where AWS fits")
| Service / AWS OSS | Role in Khidki |
|---|---|
| **AWS IoT Core** (+ Topic Rules) | Secure MQTT ingest from classroom sensor nodes (real or simulated) |
| **AWS IoT Device SDK for Python** (OSS) | Simulator/firmware MQTT client with X.509 |
| **AWS Lambda** | ingest, api, replanner, optimizer, verify, calibrate, report, agent, tts |
| **Amazon API Gateway (HTTP API)** | public API for web surfaces |
| **Amazon DynamoDB** | single-table store: rooms, telemetry (TTL), plans, nudges, fingerprints, reports |
| **AWS Step Functions** | DailyPlanSM (Map over rooms), NudgeSM (human callback + sensor verification), NightlySM |
| **Amazon EventBridge Scheduler** | 06:00 plan, 5-min replans, 16:30 reports (timezone Asia/Kolkata) |
| **Amazon Bedrock — Nova 2 Lite** (global profile) | agent reasoning; Hindi/English briefs (guarded) |
| **Strands Agents SDK** (OSS) | tool-calling agent loop |
| **Cedar** (OSS, via cedarpy) | safety + school policy + access control; masks optimizer actions |
| **Amazon Polly** (Kajal, neural, hi-IN) | spoken instructions/briefs, cached in S3 |
| **Amazon S3** | audio cache, outdoor data cache, reports, replay fixtures |
| **AWS Amplify Hosting** | web app hosting with HTTPS |
| **Amazon CloudWatch** (+ Powertools EMF/X-Ray) | logs, nudge metrics, dashboard, error alarms |
| **AWS Systems Manager Parameter Store / Secrets Manager** | API keys, demo passcodes, SimClock anchor |
| **AWS CDK** | all infrastructure as code |
| (P1) **Amazon Cognito** | real user pool with teacher/principal/parent groups |
| (P1) **AWS AppSync Events** | realtime push to tablets |
| (P2) **Amazon Transcribe** streaming | Hindi voice questions |
| (P2) **Amazon SES** | emailed parent digest (sandbox) |
| moto / LocalStack (OSS) | local mode and tests without an AWS account |

**Do not use** (deprecated or closed to new customers): Amazon QLDB, Timestream for LiveAnalytics, AWS IoT Analytics, AWS IoT Events. **Do not send SMS to Indian numbers** via SNS (requires DLT registration) — use web links/email.

### 11.3 Data flows (must work in both modes)
- **Cloud mode:** simulator → IoT Core → ingest Lambda → DynamoDB → web polls/subscribes.
- **Local mode:** simulator → `POST http://localhost:8000/ingest` → in-memory/SQLite store via the same `core` + `services` code → same web app on `localhost:5173`. Bedrock replaced by a scripted fake agent unless `AWS_PROFILE` is set. **No AWS account needed** to run `python tasks.py local`.

### 11.4 IAM and security
- One role per Lambda, least privilege; the agent Lambda has **read-only** DynamoDB access + Bedrock invoke only.
- API: passcode/Cognito JWT → Cedar authz on every route. Constant-time passcode compare. Input validation with Pydantic. Rate limit `/lab/simulate` (API Gateway throttling).
- No secrets in git: `.env.example` only. Device certs in `sim/certs/` (gitignored).
- CORS only for the Amplify domain + localhost.

### 11.5 Cost (state in README)
Lambda/API GW/DynamoDB on-demand/Step Functions/EventBridge at demo volume: cents per day. IoT Core: 1–3 simulated rooms × 2 msgs/min: negligible. Bedrock Nova 2 Lite: a few hundred calls ≈ well under $1. Polly: cached. **Create an AWS Budget alarm at $10 and $25 on Day 1.**

---

## 12. Data model — DynamoDB single table `Khidki`

| PK | SK | Attributes |
|---|---|---|
| `SCHOOL#{sid}` | `META` | name (fictional), lat, lon, nearest_station, timetable_id, policy_profile, official_grap_stage? |
| `SCHOOL#{sid}` | `ROOM#{rid}` | grade, students, volume, windows, has_purifier, sensitive_count, tier |
| `SCHOOL#{sid}` | `DAY#{date}` | outdoor forecast snapshot (raw+corrected), bias ratio, indicative GRAP, activity decisions (+policy ids), brief text, audio key |
| `ROOM#{rid}` | `TEL#{iso_ts}` | co2, pm25, temp, rh, window_contact?, occupancy?, simulated (bool) — **TTL 14 days** |
| `ROOM#{rid}` | `STATE` | latest estimate, inferred window + confidence, last_ingest_ts |
| `ROOM#{rid}` | `PLAN#{date}#v{n:03}` | plan JSON (steps, instructions, kpis, baselines, constraints) |
| `ROOM#{rid}` | `NUDGE#{iso_ts}` | instruction, task_token (encrypted/opaque), status, ack, verification evidence (implied λ, expected λ), outcome |
| `ROOM#{rid}` | `CONSTRAINT#{date}#{iso}` | reason (cold/noise/rain/exam), scope, expiry |
| `ROOM#{rid}` | `FP#{date}` | fitted λ by state, p, k, purifier eff, R², n_segments, accepted |
| `ROOM#{rid}` | `REPORT#{date}` | KPIs actual vs 4 baselines |
| `PARENT#{token_hash}` | `META` | room_id, lang, expiry |
| `AUDIT#{sid}` | `{iso_ts}#{id}` | overrides, official GRAP changes, policy decisions summary |
| `SIM` | `CLOCK` | anchor_real_ts, anchor_sim_ts, speed, scenario |

GSI1: `GSI1PK = NUDGE#OPEN`, `GSI1SK = room#ts` for active nudges. Point-in-time recovery on.

---

## 13. API contract (`services/api.py`, Powertools `APIGatewayHttpResolver`; local: FastAPI wrapper calling the same handlers)

| Method & path | Auth (Cedar action) | Purpose |
|---|---|---|
| `GET /v1/health` | none | version, clock mode, data freshness |
| `GET /v1/schools/{sid}/today` | view.school | forecast (raw+corrected), indicative/official GRAP, activity decisions + policy reasons, brief + audio URL |
| `GET /v1/rooms/{rid}/now` | view.room | latest state, inferred window, current & next instruction, open nudge id |
| `GET /v1/rooms/{rid}/plan?date=` | view.room | latest plan |
| `POST /v1/rooms/{rid}/replan` | view.room | force replan (rate-limited) |
| `POST /v1/nudges/{nid}/ack` | view.room | `{result: "done"|"cant", reason?}` → SendTaskSuccess |
| `GET /v1/rooms/{rid}/report?date=` | view.room | KPIs vs baselines |
| `GET /v1/rooms/{rid}/fingerprint` | view.room | latest fitted parameters |
| `POST /v1/schools/{sid}/override` | plan.override | override an activity decision (logged) |
| `POST /v1/schools/{sid}/grap` | grap.setOfficial | set official stage (logged) |
| `POST /v1/agent/ask` | view.room | `{room_id, question, lang}` → `{answer, tools_used[], numbers_verified: bool, audio_url?}` |
| `POST /v1/lab/simulate` | public, throttled | room params + replay date + profile → plan + 4 baselines + KPIs |
| `GET /v1/parent/{token}/today` | token | class-level digest |
| `POST /v1/sim/control` | admin | start/stop, speed, scenario, inject event |
| `POST /ingest` (local mode only) | device key | telemetry |

Define all request/response bodies as Pydantic models in `core/schemas.py`; generate TypeScript types for the web (`datamodel-code-generator` or hand-written `web/src/types.ts` kept in sync by a test).

---

## 14. Design system and UI — "The window is the interface"

The judges score **Design & usability** directly, and the last event gave a whole prize to Best UI. This section is the art direction. Treat it as binding as the API contract: tokens, type, the signature component, every screen, motion, charts, and the quality budgets. It was built from what award juries are rewarding right now (§14.1), then checked against the generic looks that make a student project read as templated (§14.2).

### 14.1 What we borrowed from award winners (and what we refused)

| Reference | What it did that won | What Khidki takes from it |
|---|---|---|
| **NYT — "See how the world's most polluted air compares with your city's"** (2019 air-pollution particle visualisation, award-entered data journalism) | Moving particles whose **density equals the real PM2.5 concentration**; narrative goes from clean baseline → your city → the worst place on Earth | **Particles are data, never decoration.** Every dot on screen stands for a fixed amount of PM2.5, identical across every window on the page, so two windows can be compared by eye. Landing narrative: clean air → a Delhi classroom today → a closed room at 2,000 ppm. |
| **Igloo Inc** (abeto, Awwwards Site of the Year 2024) | Three scroll-driven chapters, UI living *inside* the scene, particles that re-form into the next shape when you pick a link, obsessive performance work | A **scroll-scrubbed school day** on the landing page; captions sit inside the window frame, not in floating boxes; particles drift through the opening to become the next state. |
| **Messenger** (abeto, Awwwards Site of the Year 2025) | A tiny world in an extremely restricted two-colour palette; animation and performance scored highest | A **miniature world**: the principal sees the school building's facade, one lit window per classroom, panes really open or shut. A **tight palette** of six tokens, nothing improvised. |
| **Lando Norris** (OFF+BRAND, Awwwards Site of the Year 2025) | Colour system lifted straight from the subject's own object (his helmet) | Colours lifted from the **classroom itself**: blackboard green, whitewashed wall, Delhi smog, turmeric, sindoor. |
| **2026 Site-of-the-Day pattern** (Three.js scroll narratives) | One or two strong moments rather than ten; adaptive quality holding 60 fps on mobile; Lighthouse 90+; generic particle backgrounds no longer win | **One bold thing per screen**, everything else quiet. Adaptive rendering. Performance budgets are acceptance criteria (§14.10). |
| **Wakuli Impact Report** (Readymag Websites of the Year 2025, community choice) | Dense impact content made readable with a few well-placed motion moments and lots of whitespace | The **benchmark and parent report** pages: big plain sentences, one chart at a time, one reveal. |
| **CampusEvac** (this panel's Best UI, First Commit) | Two synchronised views of the same live state | Teacher tablet and principal facade update **together**; the video shows both side by side. |

Refused on purpose: full-screen WebGL on the teacher tablet (cheap hardware, real classroom), video backgrounds, decorative particle fields, glassmorphism cards, neon-on-black.

### 14.2 Design plan, checked against the defaults
Before building, Claude Code must restate this plan in `docs/design.md` and keep it current.

- **Concept:** every screen is seen *through a window*. The frame is the layout grid; the panes hold the data; whether the panes are open is the product's answer.
- **Generic looks avoided, and how:**
  - Not cream-and-terracotta: the light surface is a cool, faintly green whitewash, and the accent is turmeric, not clay.
  - Not black-with-acid-green: the dark surface is blackboard green, the real colour of Indian classroom boards.
  - Not a stack of identical rounded cards: rooms are drawn as **windows** with procedurally varied frames (paint colour, bar pattern, pane count from the room config), and radius varies by hierarchy (frames 2 px, panes 0, buttons 14 px, chips fully round).
  - No small all-caps eyebrow labels, no monospace data labels, no "→" on buttons, no middle-dot meta strings, no single highlighted word in headlines.
- **Where the boldness goes:** the `AirWindow` component (§14.5) and the Anek **width axis** in headlines. Everything else is quiet.

### 14.3 Tokens (`web/src/design/tokens.css` — CSS variables, mirrored in `tailwind.config.ts`)

**Core palette (the only brand colours allowed)**
| Token | Hex | Source in the subject | Use |
|---|---|---|---|
| `--chalk` | `#EEF0E6` | whitewashed classroom wall | light surface |
| `--blackboard` | `#1F3A30` | classroom blackboard | primary ink on light; dark surface |
| `--haze` | `#B7A27E` | Delhi winter smog sky | outdoor air, PM particles, "outside" panes |
| `--breath` | `#1C7DC0` | clear-day sky through an open window | fresh air, "open" state, Khidki's series |
| `--haldi` | `#D99A1E` | turmeric | "action due now" fills, focus halo |
| `--sindoor` | `#B3261E` | sindoor red | **only** "outdoor air severe, keep children inside" and errors |

Derived neutrals: `--ink-2 #3F564C` (secondary text, 6.9:1 on chalk), `--ink-3 #5A6C63` (muted, 4.85:1 on chalk), `--rule #C9CFC2` (hairlines), `--pane #F7F8F2` (raised surface), `--frame #DCE1D3` (window frames on light). Dark mode: surface `--blackboard`, raised `#27463A`, ink `#E7ECE2`, secondary `#B7C4BB`, rules `#3A5A4D`. Text-safe companions (checked): `--breath-ink #15669E` for blue buttons/links (chalk text on it 5.3:1); `--haldi-ink #8F5C00` for turmeric-coloured text such as the countdown (4.9:1). Raw `--haldi` (2.1:1 on chalk) is **fill only**, always with blackboard text on top (5.0:1) or beside an icon; raw `--breath` (3.85:1) is for large text, marks and illustration only. Every text/surface pair must meet WCAG AA (4.5:1 body, 3:1 large); add a contrast unit test over the token pairs.

**Chart palette (validated with the dataviz validator, OKLab ΔE; do not edit without re-running it)**
| Slot | Series | Light (on `#EEF0E6`) | Dark (on `#1F3A30`) |
|---|---|---|---|
| 1 | Khidki | `#1C7DC0` | `#4896CE` |
| 2 | CO₂ alarm | `#C2661A` | `#CF7A33` |
| 3 | Temperature-led teacher | `#2A8F63` | `#36A675` |
| 4 | Always closed | `#9A4FB0` | `#A673C6` |
| 5 | Always open | `#A0522D` | `#C46F4A` |
Light: all checks pass, worst adjacent CVD ΔE 8.8, normal-vision floor 19.5, all ≥ 3:1. Dark: all pass, worst CVD ΔE 8.8, floor 18.1. Slots 1–2 also pass **all-pairs** (ΔE ≥ 21) for scatter plots. Colour follows the policy everywhere; it never changes with filtering or rank.

**Status scale:** outdoor AQI badges use the CPCB category names and colours Delhi people already recognise, always with the category word and the number (never colour alone). Instruction states use icon + verb + colour.

**Type (`--font-ui`):** **Anek Latin** + **Anek Devanagari** (Google Fonts, one superfamily drawn by multiple designers across scripts, variable weight and width). Verify axis ranges on Google Fonts at build time; fallback `Mukta`, then system.
- Scale (1.25 ratio, rem): 0.8 · 1 · 1.25 · 1.563 · 1.953 · 2.441 · 3.815 (hero) · 5.96 (landing display).
- Body 1 rem / 1.6 line-height Latin, **1.75 for Devanagari** (matras need room); measure ≤ 68 characters.
- Weights: 400 body, 560 labels and buttons, 700 instructions, 800 display.
- Numbers: tabular figures (`font-variant-numeric: tabular-nums`) for every changing value so readings don't jitter.
- **Width as meaning:** display headlines and the teacher instruction verb use `font-stretch` — condensed (75%) when the room is shut, expanding to wide (125%) as the window opens. On the landing page the word खिड़की literally widens as you scroll the window open. Keep it to these two places.
- Sentence case everywhere, in both scripts. No all-caps labels.

**Space and shape:** 4-px base grid; section rhythm 8/12/16/24/40/64/96. Radius by role: window frame 2 px, panes 0, buttons 14 px, chips 999 px. One shadow only, for raised panes: `0 1px 0 var(--rule), 0 8px 24px -16px rgba(31,58,48,.35)` (tinted with blackboard, not grey).

**Iconography:** a custom SVG set drawn at the same stroke as Anek medium (1.75 px at 24 px): window closed, one pane ajar (cracked), one side open, both sides open, purifier on/off, child-indoors, sensor quiet. Lucide only for generic UI (menu, close, play).

### 14.4 Voice and copy
- Name things the way a teacher would: "windows", "corridor side", "road side", "air purifier", "recess". Never "λ", "ACH", "nudge", "plan v3" in the teacher or parent UI (they're fine on `/how` and `/lab`).
- **Buttons say what just happened**, and the toast repeats the same verb: instruction "Open both sides" → button **खोल दीं / I've opened them** → toast "Opened. Checking the air…" → "Air is changing ✓". Closing → **बंद कर दीं / I've closed them**. Purifier → **चालू कर दिया / Turned it on**. Secondary button **अभी नहीं हो सकता / Can't right now** → reason chips **ठंड / Too cold · शोर / Too noisy · बारिश / Raining · परीक्षा / Exam on**. (Internally these map to `result: "done" | "cant"`.)
- Errors give the fix, not an apology: "No reading from the sensor for 4 minutes. Showing the plan without live air data." Empty states invite action: "No room set up yet. Add a classroom to get its first plan."
- Hindi copy is written, not machine-translated word by word; keep a reviewed `hi.json` and note any phrase you're unsure of in LEARNINGS.

### 14.5 The signature component: `<AirWindow>` (`web/src/components/AirWindow/`)
A drawn classroom window whose contents are the live (or replayed, or simulated) air. It is the **one** memorable element; it appears once per screen at most.

```
┌──────────────┬──────────────┐   frame: --frame, 2px radius, mullion grid from room config
│ · ·  ·   ·  ·│·  ·    ·  ·  │   OUTSIDE layer (behind glass): haze-tinted sky,
│   ·    ·   · │  ·  ·    ·   │     particle density ∝ outdoor PM2.5
│  ·  ·    ·   │ ·    ·  ·    │   PANES: hinge open/closed with perspective rotateY;
├──────────────┼──────────────┤     ajar = 25°, open = 70°; one or both sides
│      ·       │     ·    ·   │   INSIDE layer (in front): particle density ∝ indoor PM2.5,
│   ·      ·   │  ·           │     drift speed ∝ air-change rate; when panes are open,
│  ~~~ warm breath haze ~~~   │     particles stream through the gap at a rate ∝ p·λ
└──────────────┴──────────────┘   BREATH: soft warm blur whose opacity ∝ (CO₂ − 400)/2,000
```
- **Encoding contract (honesty):** one particle = `PM_PER_PARTICLE` µg/m³ per unit area (default 2), identical across every `AirWindow` on the page. A visible legend under each window reads "Each dot ≈ 2 µg/m³ of PM2.5". CO₂ haze opacity uses the same mapping everywhere. If the renderer must drop particles for performance, it **changes the shared constant and the legend for all windows together**, never one window alone.
- **Rendering:** WebGL2 point sprites via a tiny library (OGL or regl, ≤ 30 KB gz) with a Canvas2D fallback; lazy-loaded. Particle motion is curl-noise drift plus a flow vector through the opening. Instanced, one draw call per layer.
- **Adaptive quality:** measure frame time over 60 frames; if > 20 ms, halve particle budget (shared constant, as above); if still slow, render a still frame and animate only on state change.
- **Teacher-tablet mode (`variant="calm"`):** Canvas2D, ≤ 400 particles, 30 fps cap, freezes to a still frame after 8 s of no change, animates only when the instruction or state changes. Battery and attention friendly.
- **Reduced motion:** static illustration with the same densities, panes drawn in their state, numbers shown beside it.
- **Accessibility:** `role="img"` with an `aria-label` generated from the data ("Windows closed. Outside PM2.5 188, inside 74. CO₂ 1,620 ppm and rising.").
- **Props:** `{ outdoorPm, indoorPm, co2, window: 'closed'|'cracked'|'open_one'|'open_both', purifier, panes, framePaint, variant: 'hero'|'calm'|'mini'|'compare', simulated }`. Storybook-style dev page at `/dev/window` with sliders.

### 14.6 Screens

**Landing `/` — a scroll-scrubbed school day** (GSAP + ScrollTrigger; Lenis smooth scroll only when reduced motion is off)
```
┌──────────────────────────────────────────────────────────────────────┐
│  Khidki                                         Lab   How it works  हिं│
│                                                                      │
│     खिड़की खोलें                ┌─────────── AirWindow (hero) ──────┐  │
│     या बंद रखें?                │  real replay: 12 Nov 2025,        │  │
│     Open the window,           │  East Delhi, 07:30                 │  │
│     or keep it shut?           │                                    │  │
│                                └────────────────────────────────────┘  │
│  07:30 ━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13:30      │
│                       scroll to move through the school day           │
└──────────────────────────────────────────────────────────────────────┘
```
Pinned chapters, one window, scroll moves the clock:
1. **Shut.** Panes closed; breath haze thickens, CO₂ counter climbs past 1,500 and 2,000. Headline stays condensed.
2. **Open.** Panes swing open; haze clears, smog particles pour in, indoor PM climbs. Headline widens.
3. **Khidki.** The day replays with Khidki's plan: an "air ribbon" (one stripe per 5 minutes, coloured by window state) builds under the window; the recess purge visibly flushes the room. Caption gives the day's two numbers from the benchmark.
4. **Five windows, one morning.** The single window splits into five small windows (one per policy) side by side, still in sync with scroll.
5. **How it works.** Plan → instruction → check the air → re-plan, drawn as air moving through the AWS architecture (Mermaid-derived SVG, path animation on scroll).
6. **Try it.** Two plain buttons: "Open the Lab" and "See the teacher's screen". Credits and data attribution in the footer.
The day shown is a **real 2025 replay** with the date and "simulated classroom, real outdoor air" in the caption.

**Teacher `/teacher/:roomId` — calm, one decision** (designed for a ₹8–10k tablet at 1024×600, landscape)
```
┌──────────────────────────────────────────────────────────────────────┐
│ कक्षा 6B          बाहर: AQI 372  बहुत ख़राब           10× सिमुलेशन ▣  │
│                                                                      │
│  ┌──────── AirWindow (calm) ───────┐   दोनों तरफ़ की                   │
│  │                                │   खिड़कियाँ खोलिए                  │
│  │                                │   Open both sides                  │
│  │                                │                                   │
│  └────────────────────────────────┘   4 मिनट के लिए       ⏱ 3:42      │
│  Each dot ≈ 2 µg/m³                                                  │
│                                       CO₂ 1,620 और बढ़ रहा है; बाहर का  │
│                                       PM अभी आज सबसे कम है (118)       │
│  ┌──────────────────────────┐  ┌──────────────────────────┐          │
│  │   खोल दीं                 │  │ अभी नहीं हो सकता          │          │
│  │   I've opened them       │  │ Can't right now          │          │
│  └──────────────────────────┘  └──────────────────────────┘          │
│ ▁▂▃▅▆▇ CO₂      ▃▃▃▂▂ PM2.5            अगला: 10:10 रिसेस में पूरी हवा बदलें │
└──────────────────────────────────────────────────────────────────────┘
```
- Two columns: the window on the left, the instruction on the right, left-aligned text. The instruction verb is set at weight 700 and its width follows the window state.
- **Keep-closed state is small and quiet**: the window, one line ("सब ठीक है — खिड़कियाँ बंद रखें / All fine, keep them shut"), the next planned change. No buttons.
- **The orchestrated moment:** when a new instruction arrives, panes in the illustration swing to the target state and the countdown starts; on verification the breath haze clears and "Air is changing ✓" appears for 2 s. Nothing else on this screen moves by itself.
- Partial-open follow-up appears in the same slot: "Only one side seems open — open the corridor side too."
- Touch targets ≥ 64 px; the primary button sits where a right thumb rests; everything readable from 2 m (instruction ≥ 2.441 rem).
- Offline: window greyed to `--rule`, line "No connection for 3 min — last instruction shown".

**Principal `/school/:schoolId` — the school facade** (Messenger-style miniature world)
```
┌──────────────────────────────────────────────────────────────────────┐
│ Demo Sarvodaya Vidyalaya (fictional)      Indicative GRAP: Stage II   │
│ Thursday 12 Nov             official stage: set ▸        ▶ आज का सार    │
│                                                                      │
│   ╔══════════════════ school facade (SVG) ═══════════════════════╗   │
│   ║  [3A ▣purifier] [3B ▯] [4A ▯] [4B ◫ajar]                      ║   │
│   ║  [6A ▯] [6B ◨open ✓] [7A ▯] [7B ◫ needs action ●haldi]        ║   │
│   ║  ─────────────── assembly ground ────────────────             ║   │
│   ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                      │
│  Outdoor PM2.5 today (bias-corrected)     Today's decisions          │
│  ▂▃▅▇▇▆▅▃▂▂▃▄  school hours shaded        Assembly  indoors  S2: 142  │
│                                           PE (6B)   indoors  S2: 128  │
│                                           Recess    outdoors  ok      │
└──────────────────────────────────────────────────────────────────────┘
```
- Each classroom is a small window on an SVG elevation of the building, generated from room config; frames vary by floor and paint; panes show the real state; a haldi dot marks rooms with an action due; a ✓ for verified. Hover/focus shows the room's CO₂/PM; click opens a side sheet with that room's day.
- Decisions list shows the policy and the number that triggered it; "Override" opens a short form asking for the reason (logged).
- Reports tab: small multiples per room (PM dose and CO₂ minutes vs baselines), never a dual-axis chart.

**Parent `/parent/:token` — a short letter**
A single column (≤ 60 ch), Hindi first, like a note from the class teacher: one mini `AirWindow` (still), two big sentences with the day's numbers, whether PE was inside and why, a ▶ listen button (Polly), and the footer "Class-level information only. Khidki is not a medical device." One reveal on load, nothing else animated.

**Lab `/lab` — five windows, one day**
- Left rail: room size, students, windows per side, purifier, replay date (real 2025 days with their AQI), profile.
- Main: **five `AirWindow`s in a row** (variant `compare`, one per policy, labelled with the policy name in its series colour) playing the same day in sync, with a shared time scrubber and play/pause.
- Below: small multiples sharing the time axis — CO₂ (ppm) on one chart, indoor PM2.5 on another, one line per policy in its slot colour, legend plus direct labels at line ends, crosshair tooltip.
- Pareto scatter: PM dose vs minutes above 1,500 ppm; only Khidki (slot 1) and CO₂ alarm (slot 2) in colour, the other three in `--ink-3` with direct labels; table view toggle.
- "Copy link to this scenario" button (state in the URL).

**How `/how`** — a long-read essay layout: the two equations (KaTeX), the parameter table, the Cedar policies in a readable code panel, data sources with attribution, limitations. Wide margins, the window diagram once.

### 14.7 Motion rules
- **One orchestrated moment per screen** (listed above). No fade-in-on-scroll for every section, no hover animation on every card.
- Motion responds to people or to real data changes; durations 180–320 ms for UI, 600–900 ms for the pane swing; easing `cubic-bezier(.2,.7,.2,1)`.
- `prefers-reduced-motion: reduce` → no scroll-scrub (chapters become stacked static figures), no particle motion, pane state shown instantly.
- Sound is off by default. A small speaker toggle plays Polly voice for instructions; no ambient audio.

### 14.8 Charts (follow the dataviz method)
- Forms: line small multiples for CO₂ and PM over the day (never two y-axes on one chart); the air ribbon (one stripe per 5 min) for window state; scatter for the Pareto; stat sentences instead of charts when the point is one number.
- Marks: 2 px lines, ≥ 8 px markers, recessive grid in `--rule`, axis text in `--ink-2`, values and labels in ink colours (never in the series colour).
- Every chart: legend when ≥ 2 series, direct labels for ≤ 4, hover tooltip, keyboard focusable points, and a "Show as table" toggle.
- Sequential (indoor PM in the ribbon or heat strips): one hue, `--haze` light → dark, with a scale legend.
- Recharts is fine for the line/scatter charts; the air ribbon and facade are hand-written SVG.

### 14.9 Tech for the UI
React + Vite + TypeScript, Tailwind reading the CSS variables, **Motion** (motion.dev) for UI transitions, **GSAP + ScrollTrigger** for the landing scrub only, OGL/regl for `AirWindow` (lazy), Recharts, KaTeX on `/how`, TanStack Query for data. Route-level code splitting: the teacher and parent routes must not load GSAP, KaTeX or the WebGL renderer.

### 14.10 Quality budgets (acceptance criteria for Phase 5)
| Route | Budget |
|---|---|
| Teacher, Parent | initial JS ≤ 170 KB gzip; LCP ≤ 2.0 s on throttled "Fast 4G, mid-tier mobile"; Lighthouse Performance ≥ 90 and Accessibility ≥ 95; works at 1024×600 and 390×844 |
| Landing, Lab | LCP ≤ 2.5 s (hero window can stream in after the headline); 60 fps target on a mid laptop with adaptive quality; Lighthouse Performance ≥ 85, Accessibility ≥ 95 |
| All | CLS < 0.05; visible keyboard focus (2 px `--blackboard` ring at 2 px offset with a 4 px `--haldi` halo outside it, so the ring itself is 10:1 against chalk); text contrast AA in light and dark; `lang="hi"` on Hindi spans; screen-reader live region announces new instructions politely |

**Design QA loop (do it, don't skip it):** a Playwright script screenshots every route at 1024×600, 390×844 and 1440×900 in light, dark and reduced-motion, writes them to `docs/screens/`, and Claude Code reviews them for overlap, clipped Devanagari, contrast and anything that reads as a template, then fixes and re-shoots. Keep the latest set in the repo; they double as README images and blog figures.

---

## 15. Simulator, SimClock, local mode, demo controls

### 15.1 Simulator (`sim/`)
- Uses the same `core.physics` with **hidden "true" parameters** that differ from defaults (so fingerprinting has something to learn), plus sensor noise (CO₂ ±30 ppm + 3%, PM ±5 µg/m³ + 10%), 30-s publish interval.
- Outdoor series: live Open-Meteo (cloud demo) or a cached replay day.
- **Teacher behaviour model:** follows a nudge with probability `p_follow` (default 0.8) after a delay ~ U(30, 120) s; scenario flags can force "ignores", "opens only one side" (λ = λ_OPEN × 0.45), "taps confirm but doesn't open".
- Timetable: assembly 07:30–07:50 (outdoor/indoor per decision), 8 periods × 40 min, recess 10:10–10:40 (class leaves unless outdoor activity forbidden → stays inside), PE period 6 for 6B.
- Publishes to IoT Core (`awsiotsdk`, X.509 certs from `scripts/provision_device.py`) or to local `/ingest`.
- Scenarios (`sim/scenarios/*.yaml`): `severe_morning` (replay of a Stage III day), `partial_open` (the aha moment), `teacher_cant_cold`, `forecast_spike`, `purifier_room`.

### 15.2 SimClock (`core/clock.py`)
- `now()` returns real time in LIVE mode; in DEMO mode returns `anchor_sim + (real_now − anchor_real) × speed`, reading the anchor from SSM/DynamoDB `SIM/CLOCK` (cached 5 s).
- Every component (ingest, planner, Step Functions wait computation, UI) uses SimClock. Step Functions `Wait` uses `SecondsPath` computed by a Lambda = sim_seconds / speed.
- UI shows the **⏩ N× SIM** badge whenever speed > 1 or data is simulated. Never hide it.

### 15.3 Local mode
`python tasks.py local` → starts FastAPI (port 8000) with in-memory store + local Cedar + optimizer + fake agent (scripted, still runs the number-fidelity guard) + simulator at 10× + Vite dev server (5173). Opens the teacher page. Works offline with cached replay data. This is the "Build It" path — document it first in the README.

### 15.4 Optional hardware (P2, only if the team has parts)
ESP32 + Sensirion SCD4x (CO₂/temp/RH) + Plantower PMS5003 (PM2.5), MicroPython or Arduino, publishing the same JSON to IoT Core over MQTT/TLS. Put sketches in `firmware/`. Even one real node on a desk in the video massively boosts credibility; the system must work fully without it.

---

## 16. Repository layout, tooling, commands

```
khidki/
├─ README.md                    # story → try locally → live URL → where AWS fits → benchmark → safety → limitations → credits → AI tools used
├─ docs/
│  ├─ SPEC.md                   # this file
│  ├─ architecture.md / .png    # Mermaid + rendered PNG
│  ├─ physics.md                # equations, parameters, citations
│  ├─ safety.md                 # policies, LLM guard, privacy, honesty rules
│  ├─ benchmark.md              # generated results table + Pareto image
│  ├─ design.md                 # §14 plan restated + decisions log
│  ├─ screens/                  # Playwright screenshots per route/viewport/theme (design QA)
│  ├─ demo-script.md            # §21
│  ├─ submission.md             # §22 writeup text
│  ├─ blog.md                   # §22 blog draft
│  ├─ runbook.md                # §20
│  ├─ LEARNINGS.md              # what fought back (running log)
│  └─ CREDITS.md                # data/library attributions & licences
├─ core/khidki_core/            # pure Python: physics, dose, aqi, grap, optimizer, inference, calibration, baselines, clock, schemas, policy/
├─ data/khidki_data/            # openmeteo.py, cpcb.py, openaq.py (optional), bias.py, cache.py ; fixtures/replay/*.json
├─ services/khidki_services/    # lambda handlers: api, ingest, planner, replanner, nudge_issue, nudge_verify, calibrate, report, brief, tts, agent, sim_control
├─ agent/khidki_agent/          # strands agent, tools, prompts (hi/en), guard.py, fake_agent.py
├─ sim/                         # simulator.py, teacher_model.py, scenarios/*.yaml, certs/ (gitignored)
├─ local/                       # FastAPI app wiring services to in-memory store
├─ infra/                       # CDK app (Python): stacks/{data,ingest,compute,workflows,api,web,observability}.py
├─ web/                         # Vite React app: src/design/tokens.css, src/components/AirWindow/, src/i18n/, routes/
├─ bench/                       # run_benchmark.py, results/
├─ firmware/                    # optional
├─ tests/                       # pytest (unit, policy, contract with moto, guard, e2e-local)
├─ scripts/                     # provision_device.py, seed_demo.py, fetch_replay.py, synth_phrases.py, render_arch.py
├─ tasks.py                     # cross-platform task runner (Windows-friendly; no make required)
├─ pyproject.toml / uv.lock     # uv workspace
└─ .github/workflows/ci.yml     # ruff, mypy (core), pytest, cedar validate, web typecheck+build
```

**Toolchain:** Python 3.12 + `uv`; Node 20+; AWS CLI v2; CDK v2 (`npm i -g aws-cdk`); Docker optional.
**Lambda packaging without Docker:** build a dependency layer with
`pip install --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --only-binary=:all: -t build/layer/python -r requirements/lambda.txt`
(numpy, cedarpy, pydantic, aws-lambda-powertools, strands-agents). Keep SciPy **out** of Lambda. If the agent layer exceeds limits, split into its own layer or use `DockerImageFunction` (requires Docker).

**`tasks.py` commands** (each prints what it does):
`setup` · `test` · `lint` · `local` · `fetch-replay` · `bench` · `cdk-synth` · `deploy` · `provision-device` · `seed-demo` · `sim --scenario severe_morning --speed 10 --target cloud|local` · `synth-phrases` · `web-build` · `web-deploy` · `demo-reset` · `arch-diagram`.

---

## 17. Build plan

### 17.1 Pre-kickoff checklist (allowed now: learning/planning/practice — **no project code, no project repo**)
- [ ] Every team member: register for the tour, **check in to Environmental Hacks**, create AWS Builder Center profile and **verify student status** (needed for the Amazon interview track).
- [ ] Create the AWS account now (debit/RuPay ok, ~₹2 verification). Turn on MFA. Create an IAM admin user/SSO for CLI. **Set AWS Budgets alarms ($10, $25).**
- [ ] In `ap-south-1`: open Bedrock console → confirm Nova 2 Lite is usable via `global.amazon.nova-2-lite-v1:0` (run one `converse` call from CLI/boto3 in a scratch shell). If a model-access page exists in the console, request access.
- [ ] `aws polly describe-voices --engine neural --language-code hi-IN --region ap-south-1` → confirm Kajal.
- [ ] Register for a data.gov.in API key; test one call; note fields.
- [ ] Install toolchain (uv, Node 20, AWS CLI, CDK, VS Code + Claude Code). `cdk bootstrap aws://ACCOUNT/ap-south-1`.
- [ ] Practice in a **throwaway** sandbox (not reused): a Strands "hello tool" agent; a cedarpy `is_authorized` call; a CDK Lambda + HTTP API; an IoT Core MQTT publish from the test client. Delete the sandbox afterwards.
- [ ] Join WeMakeDevs Discord + Builder Center space; post an intro (not the idea's code).
- [ ] Decide team roles (§17.4). Apply on Luma for the DTU day if you want mentor feedback (AWS mentors include an AI/ML lead consultant and database engineers).
- [ ] Re-read this spec; prepare the shot list for the video (§21).

### 17.2 Phases with acceptance criteria (P0 = must ship; P1 = should; P2 = stretch)
| # | Phase | Scope | Acceptance (all must pass) | Target |
|---|---|---|---|---|
| 0 | Scaffold | repo layout, uv workspace, tasks.py, CI, pre-commit (ruff), `.env.example`, LICENSE (Apache-2.0), LEARNINGS, CREDITS | `python tasks.py test` runs (0 tests ok); CI green | Thu +1 h |
| 1 | Core science **P0** | physics, dose, aqi, grap, baselines, optimizer (DP + Lagrangian budget + masks hook), inference, calibration, schemas | physics sanity tests (§7.1); AQI tests; optimizer never exceeds budget, beats ALWAYS_CLOSED on CO₂ and ALWAYS_OPEN on PM on a synthetic severe day; calibration recovers params (§8.3); replan < 3 s locally | Thu night |
| 2 | Data + sim + local **P0** | Open-Meteo/CPCB fetchers + bias, replay fixtures, simulator + scenarios, SimClock, local FastAPI; **design tokens + fonts + `AirWindow` (calm variant)** + first teacher screen | `python tasks.py local` → teacher page shows instructions changing over a simulated day with the window illustration; `partial_open` scenario produces a PARTIAL outcome; `/dev/window` sliders work | Fri morning |
| 3 | Policy + agent skeleton **P0** | Cedar schema/policies, validation, optimizer masks, activity decisions with policy IDs; agent tools + fake agent + number guard | policy table tests; S1 blocks OPEN in severe air unless CO₂≥2000; guard rejects an invented number | Fri midday |
| 4 | AWS infra **P0** | CDK: DynamoDB, IoT thing/policy/rule, Lambdas + layer, HTTP API, Step Functions (Daily, Nudge, Nightly), Scheduler, SSM params, CloudWatch dashboard/alarms | `python tasks.py deploy` idempotent; simulator → IoT Core → DynamoDB visible; a NudgeSM execution goes green end-to-end in console; `/v1/health` live | Fri night |
| 5 | Web app **P0** | teacher, school facade, parent letter, Lab (five windows), how, scroll-scrubbed landing; `AirWindow` hero/compare/mini variants; Amplify deploy; Polly cached phrases | all §14.10 budgets met; token contrast test green; Hindi/English toggle; SIM badge + particle legend visible; reduced-motion and dark mode verified; **design QA screenshots** in `docs/screens/` reviewed and fixed | Sat afternoon |
| 6 | Bedrock agent + briefs **P0** | Strands agent on Nova 2 Lite with tools; morning brief + parent digest via LLM with guard + template fallback | 10 scripted questions (hi/en) answered with verified numbers; forced Bedrock failure → template answer | Sat evening |
| 7 | Benchmark + nightly **P0** | bench over replay days; NightlySM fingerprint + reports | `docs/benchmark.md` + Pareto PNG generated; school page shows yesterday's report; fingerprint card shows fitted λ | Sat night |
| 8 | Polish + docs **P0** | README, architecture PNG, safety.md, physics.md, runbook, demo scenario rehearsal | fresh clone → `python tasks.py local` works on a second machine; all docs present | Sun 11:00 |
| — | **FEATURE FREEZE** | only bug fixes after this | | **Sun 12:00** |
| P1 | Cognito groups; AppSync Events realtime; agent text box on teacher/school page; parent digest audio | each behind a flag; never break P0 | Sat/Sun if ahead |
| P2 | Transcribe Hindi voice; SES parent email; ESP32 node; robust-forecast plan mode; OpenAQ calibration of replay | only if P0+P1 done | |

### 17.3 Day-by-day (IST)
- **Thu 8 Oct** — kickoff → create repo, commit SPEC → Phase 0 → Phase 1. Fetch and inspect CPCB + Open-Meteo payloads. Evening: replay fixtures.
- **Fri 9 Oct** — Phase 2 → Phase 3 → Phase 4 (deploy early, deploy often). Night: first end-to-end in cloud.
- **Sat 10 Oct** — (optional DTU visit: show the Lab + teacher card to mentors, ask "what would make you trust this?") Phase 5 → Phase 6 → Phase 7. Write the blog draft from LEARNINGS.
- **Sun 11 Oct** — Phase 8 by 11:00 → freeze 12:00 → record video (2 takes) → edit → upload (unlisted) → test signed-out → publish blog on Builder Center → submit form **≥ 3 h before deadline**.

### 17.4 Team split (if 2–4 people)
- **A — Science & optimizer** (core/, bench/, physics.md)
- **B — Cloud & workflows** (infra/, services/, IoT, Step Functions, observability)
- **C — Web & UX** (web/, design tokens, `AirWindow`, landing scroll story, i18n, Polly phrases, accessibility, design QA)
- **D — Agent, policy, story** (agent/, policy/, video, blog, writeup)
Solo: follow the phase order strictly; skip P1/P2.

---

## 18. Testing strategy ("tests are the spec")
- `tests/test_physics.py` — exact solution vs fine-step Euler; steady states (§7.1 numbers); monotonicity; a→0 edge case.
- `tests/test_aqi_grap.py` — breakpoint examples (45→75, 150→~323), boundaries, stage mapping.
- `tests/test_optimizer.py` — budget respected; masks respected; dominates trivial baselines on synthetic days; deterministic output for fixed inputs; runtime bound.
- `tests/test_inference.py` — window state recovered from simulated CO₂ with noise (≥ 90% accuracy over scenarios).
- `tests/test_calibration.py` — parameter recovery bounds; rejects non-physical fits.
- `tests/test_policy.py` — schema validation; every policy has a positive and negative case; override requires principal.
- `tests/test_guard.py` — numbers present → pass; invented number → template; rounding tolerance; Devanagari numerals handled.
- `tests/test_api_contract.py` — moto-backed DynamoDB; every route's auth + schema.
- `tests/test_nudge_flow.py` — local state-machine emulation of NudgeSM branches (done+match, done+mismatch, no_ack+match, cant).
- `tests/test_e2e_local.py` — spin local app, run `severe_morning` at 60× for a simulated morning, assert ≥ 1 VERIFIED and report generated.
- Web: `tsc --noEmit`, a Playwright smoke test of the teacher page (P1).

---

## 19. GUARDRAILS (hard rules for Claude Code)

### Hackathon compliance
1. Never generate project code before the human confirms the hackathon has started. First commit = `docs/SPEC.md` only.
2. Commit at least every 1–2 hours with meaningful messages. Never rewrite/squash history.
3. Maintain `docs/CREDITS.md` (libraries + licences, Open-Meteo/CAMS attribution, data.gov.in GODL-India) and an "AI tools used: Claude Code" line in README and writeup.
4. Every feature claimed in README/writeup must be demonstrable in the running app.

### Honesty and safety
5. **Never present simulated data as measured.** Every simulated value carries `simulated: true`; the UI shows the SIM badge. Personas and the school are labelled fictional.
6. Benchmark results are always labelled "simulation with real outdoor data, not a field trial". Report losses honestly.
7. Khidki is **not a medical device**; no diagnosis, no medical advice; for health issues direct to a doctor. Show this in footer and parent page.
8. Khidki **never contradicts official DoE/CAQM orders**; it only reminds and links.
9. Safety policies (Cedar S1–S4) cannot be disabled by teachers; only principals can override activity decisions, always logged.

### LLM discipline
10. The LLM **never decides or changes** plans, policies or actions. Code + Cedar decide; the LLM explains and rephrases.
11. Every LLM output shown to users passes the number-fidelity guard or is replaced by the template.
12. No silent LLM fallbacks: if the template is used, the response says so (small "assistant offline/verified template" tag).
13. Prompts and tool outputs never include personal data.

### Privacy (India DPDP Act 2023 sensitivity — children's data needs verifiable parental consent)
14. **No child-level personal data at all.** Rooms store only counts (students, sensitive_count). Parent links are class-level and expire.
15. No faces, names of real children, or real school names in data, UI or video.

### Engineering
16. `core/` is pure Python with type hints and no AWS imports; services wrap it. Same code runs locally and in Lambda.
17. Least-privilege IAM per function; no wildcards on write actions; secrets only in SSM/Secrets Manager.
18. Region `ap-south-1` for everything except Bedrock global profile routing (and Polly fallback if needed).
19. Don't use deprecated/closed services (QLDB, Timestream LiveAnalytics, IoT Analytics, IoT Events). Don't send SMS to India.
20. Every external call has a timeout (≤ 8 s), bounded retries, and a cached fallback.
21. Keep Lambda deps small (no SciPy/pandas in Lambda). Optimizer must meet the runtime target.
22. P0 before P1 before P2. If behind schedule, cut scope — never ship a half-working feature into the video.
23. When unsure about an API, check the installed package/docs; record surprises in `docs/LEARNINGS.md`.

### Design
24. Use only the §14.3 tokens and validated chart palette. A new colour needs a reason in `docs/design.md` and, for charts, a passing run of the palette validator.
25. Particles and haze in `AirWindow` must follow the encoding contract (§14.5): one shared µg/m³-per-dot constant per page, legend always visible. Never decorative particles.
26. One orchestrated motion moment per screen; respect `prefers-reduced-motion`; teacher and parent routes never load GSAP, KaTeX or WebGL.
27. Meet the §14.10 budgets before calling Phase 5 done, and run the screenshot design-QA loop after every UI change of substance.
28. No template tells: no all-caps eyebrow labels, no monospace data labels, no "→" on buttons, no middle-dot meta strings, no identical card grids, no dual-axis charts.

---

## 20. Deployment runbook (`docs/runbook.md`)
```bash
# one-time
uv sync && (cd web && npm ci)
aws configure sso   # or access keys for an IAM user
cdk bootstrap aws://$ACCOUNT/ap-south-1
aws ssm put-parameter --name /khidki/datagov_key --type SecureString --value $DATAGOV_KEY
python tasks.py fetch-replay          # caches Oct–Dec 2025 Delhi school days
python tasks.py synth-phrases         # Polly Kajal MP3s → S3 (after deploy)

# deploy
python tasks.py test && python tasks.py deploy      # CDK deploy all stacks (idempotent)
python tasks.py provision-device --room 6B          # IoT thing + certs → sim/certs/
python tasks.py seed-demo                           # demo school, rooms 6B (no purifier) + 3A (purifier), parent token
python tasks.py web-deploy                          # build web, deploy to Amplify
python tasks.py sim --scenario severe_morning --speed 10 --target cloud

# demo reset between takes
python tasks.py demo-reset
```
Fallbacks: if CloudFront/Amplify is blocked by new-account verification, serve the web from S3 website hosting temporarily and note it; if IoT certs fight back, use the API Gateway `/ingest` route (still AWS) and fix later.

---

## 21. Demo video script (target 2:50 — must be under 3:00)

Record at 1080p, screen + voice-over (calm, Hinglish-friendly English). Use the `severe_morning` replay at 10× and `partial_open` scenario. **Show AWS on screen** — the rules require it.

| Time | Visual | Voice-over (paraphrase freely) |
|---|---|---|
| 0:00–0:12 | Landing page hero: the `AirWindow` with real Delhi air; scroll — panes shut, breath haze thickens, CO₂ counter passes 2,000; scroll — panes open, smog particles pour in; the word खिड़की widens | "On Delhi's bad-air days, every classroom faces the same trap. Shut the windows and CO₂ climbs past 2,000. Open them and the smog comes in." |
| 0:12–0:27 | Text cards: 44.9 lakh students · Surrey 2025 study finding | "Researchers fitted classrooms with CO₂ alarms. CO₂ fell — but PM went up, and teachers mostly decided by temperature. They asked for a system that balances all three. That's Khidki." |
| 0:27–0:45 | Principal's school facade at 06:00: lit windows per room, forecast curve, PE moved indoors with **Cedar policy S2** and the number; Polly Hindi brief plays 3 s | "At 6 AM Khidki plans every room's day from the live forecast, the timetable and each room's own physics — and checks school safety policy as code." |
| 0:45–1:15 | Split screen (teacher tablet + school facade in sync): quiet "keep shut" → "Open both sides — 4 min", panes swing open in the illustration → tap **I've opened them** → breath haze clears, **Air is changing ✓**, and the 6B window on the facade opens too | "Ms. Sunita sees one calm instruction. Most periods it says nothing. When she opens the windows, Khidki doesn't take her word for it — it reads the CO₂ curve and confirms the air actually changed." |
| 1:15–1:35 | `partial_open`: tapped "I've opened them", haze barely clears → "Only one side open? Open the corridor windows too." → verified | "And when only one side opened, it knows — from physics, not a window sensor." |
| 1:35–1:50 | Ask Khidki (Hindi text/voice): "Kya 11:20 pe PT bahar le jaun?" → answer with numbers + policy; show tool calls panel | "Teachers can ask in Hindi. A Strands agent on Amazon Bedrock answers with numbers from the twin and the policy — and a guard rejects any number it didn't get from a tool." |
| 1:50–2:15 | AWS console montage (fast, labelled): IoT Core MQTT client messages → Step Functions NudgeSM green graph → DynamoDB items → CloudWatch dashboard; then architecture diagram | "Sensors stream through IoT Core; Step Functions runs the nudge-and-verify loop with a human callback; EventBridge schedules planning; DynamoDB, Lambda, Polly, Amplify — all deployed with CDK in Mumbai. And it runs fully locally with Strands, Cedar and moto." |
| 2:15–2:35 | Lab: five windows playing the same real Delhi morning side by side, then the Pareto chart + benchmark table | "Replaying real Delhi air from last winter: compared with a CO₂ alarm, Khidki cuts PM dose by X% while keeping CO₂ minutes low — simulated, with real outdoor data." (fill X from results) |
| 2:35–2:50 | Parent digest in Hindi; closing card: "Khidki — open the window at the right minute." + GitHub/live URL | "Every evening a parent gets one honest line about her child's classroom air. Most days, Khidki just tells you when to breathe." |

Checklist: captions on; no real children/faces; SIM badge visible; video < 3:00; uploaded public/unlisted; link tested signed-out.

---

## 22. Writeup and blog

### 22.1 Submission writeup (≈250 words; keep in `docs/submission.md`)
**Track:** Air.
**Problem:** On high-AQI days Delhi's naturally ventilated classrooms trade CO₂ build-up (windows shut) against PM2.5 ingress (windows open). Field studies show CO₂ alarms reduce CO₂ but raise PM, and teachers decide by temperature; researchers call for a holistic, school-level ventilation signal.
**What we built:** Khidki plans each classroom's ventilation at 5-minute resolution using a physics twin, bias-corrected live outdoor forecasts and the timetable; shows one calm Hindi/English instruction on a tablet; verifies from the CO₂ curve whether windows actually opened; re-plans every 5 minutes; learns each room's air-change rates nightly; reports to principals and parents. School safety policy is code (Cedar). A Strands agent on Bedrock explains decisions with numbers it can't invent.
**Where AWS fits:** IoT Core → Lambda → DynamoDB; Step Functions (daily plan, nudge-and-verify with task-token callbacks, nightly calibration); EventBridge Scheduler; Bedrock Nova 2 Lite; Polly Kajal (Hindi); API Gateway; Amplify; CloudWatch; CDK in ap-south-1. Open source: Strands Agents, Cedar, Powertools, AWS IoT Device SDK; local mode runs with no AWS account.
**Results:** [benchmark headline, labelled as simulation with real outdoor data].
**Limitations:** simulated sensors in the demo; well-mixed room model; CAMS forecast is coarse (bias-corrected with CPCB).
**AI tools used:** Claude Code (VS Code).
**Links:** repo · live · video · blog.

### 22.2 Builder Center blog (AirPods prize) — `docs/blog.md`
Title idea: *"The window problem: optimizing a Delhi classroom's air with Step Functions, Cedar and a 5-minute dynamic program."*
Outline: the 10:05 AM dilemma → the evidence gap → the physics in 2 equations → why a DP with a Lagrangian attention budget → verifying humans with CO₂ decay (tracer-gas idea) → Cedar as the optimizer's guardrail → the number-fidelity guard for the LLM → what fought back (from LEARNINGS: e.g., CAMS bias, IoT certs, Lambda layer size, SimClock + Step Functions waits) → results & honest limits → what a school would need to pilot it. Include the architecture diagram and the Pareto chart. Publish before submitting; link it.

---

## 23. Final submission checklist
- [ ] Public GitHub repo; README top section has: one-line story, GIF/screenshot, **live URL**, **video link**, **"Run locally in 2 minutes"**, Where AWS fits table, benchmark headline, safety, limitations, credits, AI tools used.
- [ ] Live URL works in incognito on phone and laptop; demo passcode in README (demo only).
- [ ] YouTube video < 3:00, public/unlisted, opens signed-out; shows AWS console.
- [ ] Writeup pasted from `docs/submission.md`; track = **Air**.
- [ ] Builder Center blog published and linked.
- [ ] All team members checked in; Builder Center student verification done.
- [ ] Git history shows steady commits Thu–Sun.
- [ ] Budget alarm checked; nothing expensive left running (scale schedules down after judging window if needed — but keep the live URL up through results).

---

## 24. Risks, limitations, fallbacks
| Risk | Mitigation |
|---|---|
| Bedrock access/verification delay on new account | Pre-kickoff test; template fallback; local fake agent |
| CloudFront/Amplify blocked by account verification | S3 website hosting temporarily |
| CAMS under-predicts Delhi | CPCB bias correction; label uncorrected data; relative KPIs |
| data.gov.in API flaky/rate-limited | cache; fall back to Open-Meteo only with flag |
| IoT Core cert friction | API Gateway ingest fallback (still AWS) |
| Optimizer too slow in Lambda | coarser grid; numpy vectorisation; memory 1,769 MB+ |
| Lambda layer too big | split layers; drop extras; container image |
| Time overrun | strict P0 order; freeze Sun 12:00 |
| Judges doubt the physics | `/how` page + tests + citations + honest limitations |

**Stated limitations (put in README):** well-mixed single-zone model; default parameters are literature-based approximations until fingerprinted; demo sensors simulated; CO₂–cognition evidence is task-dependent; outdoor forecast resolution ~45 km; not a medical device; not a field-validated trial.

---

## 25. Why this wins — scorecard against the judging criteria

| Criterion | What judges will see |
|---|---|
| **Idea & Impact** | A real, daily, Delhi-specific problem; a named teacher; a quantified change per classroom (PM dose ↓, CO₂ minutes ↓) with a credible path to 5,556 schools (Tier 0 needs no hardware). Directly answers a published research gap. "Small problem solved well." |
| **Built on AWS** | 12–15 AWS services each with a job, CDK IaC, deployed in Mumbai, **plus** AWS open source (Strands, Cedar, Powertools, IoT Device SDK) and a no-account local mode — eligible under both paths. |
| **Design & usability** | A distinctive, subject-born visual identity (classroom palette, Anek width-as-meaning, data-true `AirWindow`) applied with award-level restraint; one calm decision for a busy teacher; a school you can read at a glance as a building; Lab anyone can play with; measured budgets for speed and accessibility. Competes for the same qualities that won Best UI last time. |
| **Execution** | Works end-to-end live; tests; verified loop; benchmark; fingerprinting; graceful degradation. |
| **Demo video** | A clear dilemma → three "aha" moments (verified ✓, partial-open detection, policy-reasoned PE decision) → AWS console proof → Pareto proof → human close. |
| **Amazon interview signal** | Engineering depth reviewers respect: optimisation, system identification, policy-as-code, human-in-the-loop workflows, observability, tests, honest limits. |
| **Differentiation** | Not a dashboard, not a chatbot, not a FIRMS map. Indoor + control + verification is rare in student climate hacks. |

No project can be *guaranteed* to win — the panel's judgement is final and unknowable — but this design maximises every scored dimension and mirrors exactly what this organiser rewarded last time.

---

## 26. Sources (verify links still resolve; cite in `docs/CREDITS.md` / `docs/physics.md`)
- Hackathon: <https://www.wemakedevs.org/aws/env> · rules <https://www.wemakedevs.org/aws/env/rules> · schedule <https://www.wemakedevs.org/aws/env/schedule> · tour rules <https://www.wemakedevs.org/aws/rules>
- First Commit winners: <https://www.wemakedevs.org/aws/first-commit/projects> · Suraksha <https://github.com/harshendram/firstcommit-hack> · Beacon <https://github.com/Prashant-thakur77/Beacon> · CampusEvac <https://github.com/AfreenInnovates/campus> · top blogs <https://www.wemakedevs.org/aws/first-commit/projects/blogs>
- Rawat N., Kumar P., et al. (2025) IoT-driven acoustic and visual CO₂ feedback in classrooms, *Sci. Total Environ.* 980:179543, doi:10.1016/j.scitotenv.2025.179543
- Rawat N., Kumar P. (2024) Air purifier and scheduled natural ventilation in a near-highway school, *J. Building Eng.* 86:108813, doi:10.1016/j.jobe.2024.108813
- Allen J.G. et al. (2016) Associations of cognitive function scores with CO₂, ventilation and VOC exposures, *Environ. Health Perspect.* (COGfx)
- Persily A., de Jonge L. (2017) Carbon dioxide generation rates for building occupants, *Indoor Air* 27(5):868–879
- REHVA Journal — Healthy low-energy redesigns for schools in Delhi (field study of five Delhi-area schools)
- Delhi PM2.5 diurnal/boundary-layer behaviour: EGU22-9142 (neighbourhood-scale PM2.5 variability in Delhi, post-monsoon/winter); Murthy et al. (2020) mixing layer height and winter air quality in Delhi, *JASTP* 197
- Indoor PM mass-balance parameters: LBNL black-carbon infiltration study (P≈0.97, k≈0.08 h⁻¹); Beijing window-crack infiltration study (P≈0.93, k≈0.10 h⁻¹)
- CPCB National AQI breakpoints (2014 methodology); GRAP stages and revised school measures (CAQM, Dec 2024; DoE Delhi circulars at edudel.nic.in)
- UDISE+ 2024-25 Delhi school/enrolment figures (Ministry of Education parliamentary annexures; press coverage)
- Open-Meteo Air Quality API (CAMS) <https://open-meteo.com/en/docs/air-quality-api> — attribution required
- data.gov.in Real-time AQI resource `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`
- Amazon Bedrock Nova 2 Lite model card & regional availability (global profile from ap-south-1) — docs.aws.amazon.com/bedrock
- Amazon Polly bilingual voices (Aditi, Kajal: en-IN/hi-IN) — docs.aws.amazon.com/polly
- Strands Agents SDK <https://github.com/strands-agents> · cedarpy <https://pypi.org/project/cedarpy/>
- **Design references (§14.1):** Awwwards Sites of the Year <https://www.awwwards.com/websites/sites_of_the_year/> (Igloo Inc and Messenger by abeto; Lando Norris by OFF+BRAND) · Igloo Inc case study <https://awwwards.com/igloo-inc-case-study.html> · Messenger <https://www.awwwards.com/sites/messenger> · Lando Norris design notes <https://designrush.com/best-designs/websites/lando-norris-website-design> · 2026 immersive-winner trends <https://digitalstrategyforce.com/journal/why-are-immersive-experiences-dominating-the-2026-awwwards/> · Readymag Websites of the Year 2025 <https://blog.readymag.com/websites-of-the-year-2025/> · NYT air-pollution particle piece (via FlowingData) <https://flowingdata.com/2019/12/04/compare-your-citys-air-pollution-to-the-rest-of-the-world/> · Climate TRACE air pollution (Webby 2026 data-viz nominee) <https://winners.webbyawards.com/2026/websites-and-mobile-sites/features-design/best-data-visualization/368572/climate-trace-air-pollution>
- Anek Devanagari / Anek Latin (Google Fonts, Ek Type) <https://fonts.google.com/specimen/Anek+Devanagari>
