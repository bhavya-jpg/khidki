# Khidki audit, as an Environmental Hacks judge would see it

Audited Sat 10 Oct 2026, 20:25 to 21:20 IST, at commit `f570158` (25 commits, all pushed). No code was
changed during the audit. Every status below is backed by a command that was run, a file and line, a URL or
a screenshot. Raw evidence is in [`docs/audit-evidence/`](audit-evidence/) and
[`docs/screens/audit/`](screens/audit/).

Status key: **PASS** (evidence shows it holds), **WARN** (works but a judge could mark it down),
**FAIL** (missing, broken or untrue as claimed).

> **Status on Sun 11 Oct, after the audit.** This is a snapshot of Sat 10 Oct, 20:25 to 21:20 IST. Since then:
> the reason line, navigation and 404, font weight, CREDITS additions, budget alarm and API throttling,
> Override on the live site, the demo-reset failure, the README's live link and Bedrock wording, the blog,
> and an explainer video were done. Three findings turned out to share real causes that are now fixed: the
> one-side catch (readings were expiring in DynamoDB, and the verification window was one reading short), and
> the dead live page (it now runs while someone is watching). Still open: the open-close-open flip-flop in
> local mode, the demo script and writeup files, "(verify)" marks in `physics.md`, and Bedrock.

**The short version.** The engineering is real: 125 tests pass, CI is green, a fresh clone runs locally in
two commands, and a 46-resource CDK stack is live with 20 successful Step Functions executions. What a
judge cannot see yet is the submission itself: there is no demo script, no video, no writeup and no blog,
and the README still says "work in progress". Four things that would be on camera are not reliable today:
the live page is frozen when no simulator is running, the principal's Override button fails on the live
site, the "only one side opened" catch depends on timing, and the plan asks to open, close and open again
within six minutes.

---

## A. Submission requirements

### 1. Public repository readiness: PASS (two small WARNs)
| Check | Status | Evidence |
|---|---|---|
| No AWS keys, tokens or private keys in history | PASS | `git log -p --all` searched for `AKIA…`, `ASIA…`, `aws_secret_access_key`, `BEGIN … PRIVATE KEY`, `ghp_`, `github_pat_`, `sk-`, `xox`: 0 matches. `gitleaks` is not installed, so this was a pattern scan, not a full scanner run. |
| Demo keys never committed | PASS | The two values in `.env` were searched for in `git log -p --all`: 0 matches each. |
| No account ID or resource IDs committed | PASS | The AWS account ID: 0 matches in history. Amplify app id, API id and bucket name: 0 matches in tracked files. `infra/outputs.json` is gitignored. |
| `.env`, certs, CDK output ignored | PASS | `.gitignore` lists `.env`, `.env.*`, `sim/certs/`, `infra/cdk.out/`, `cdk.context.json`, `infra/outputs.json`. Only `.env.example` was ever added. |
| LICENSE present | PASS | `LICENSE` (Apache-2.0). |
| `.env.example` is current | WARN | It says `AWS_REGION=ap-south-1` and lists three passcode variables the code no longer reads. Fix: set the region to `ap-southeast-2`, replace the passcodes with `KHIDKI_DEVICE_KEY` / `KHIDKI_ADMIN_KEY` (empty). |
| Author identity | WARN | Commits carry a personal Gmail address, which is visible in a public repo. Nothing to fix unless you would rather it was the GitHub no-reply address; history must not be rewritten either way. |

### 2. Demo video plan: FAIL (blocker)
`docs/demo-script.md` does not exist (`ls docs`). There is no video. The rule is "if the video does not show
it, it does not count", so nothing counts yet.
Fix: write a timed 2:40 script that shows only features marked WORKS in section 15, then record it. A
proposed script is in section 16.

### 3. Writeup draft: FAIL (blocker)
No `docs/submission.md`. The AI tool is already named in `README.md` ("AI coding tools used: Claude Code")
and in the landing page footer, which is good.
Fix: write about 250 words covering the problem, the build, where AWS fits and the AI tool.

### 4. Feature honesty: WARN, with three claims that must change
Every claim in `README.md` and on the landing page, checked against running code:

| Claim | Where | Status | Evidence |
|---|---|---|---|
| Plans in 5-minute steps from forecast, timetable and a physics model | README | PASS | `core/khidki_core/optimizer.py`, `planning.py`; `tests/test_optimizer.py`, `test_physics.py` pass. |
| Safety rules are Cedar policies (S2: PE moves indoors above PM2.5 90) | README | PASS | `core/khidki_core/policy/khidki.cedar`; `tests/test_policy.py`; the principal page shows "S2, S3 … (forecast 190 µg/m³)" (`docs/screens/audit/live-school-desktop-light.jpg`). |
| One calm Hindi/English instruction | README | PASS | `docs/screens/audit/local-teacher-phone-light.jpg`. |
| Reads the CO₂ curve to check the window opened | README | PASS | Local run: "issued → tapped → verifying → verified" with λ 4.58 against 6.0 expected (`audit-evidence/partial-open-repro.log`). |
| "asks for the corridor side if only one side did" | README, landing | **WARN: timing-dependent** | Caught in 3 of 6 runs, and missed on the live stack. See section 15. |
| "never asks more than 6 times a day" | README | PASS, but see flip-flop | Budget cap in `engine._maybe_issue`; `test_severe_morning_verifies_and_respects_budget` passes. Three of the six are spent in the first six minutes (section 15). |
| "answers questions in Hindi with numbers it can't make up" | README, landing | **WARN: API only** | `POST /v1/agent/ask` works live and returns `"source":"template","numbers_verified":true`. There is no "Ask Khidki" anywhere in `web/src` (`grep -rn "agent/ask" web/src`: no matches). It cannot appear in the video as built. |
| "'Ask Khidki' is a Strands Agents agent … phrase answers with Amazon Bedrock" | README | **FAIL as stated** | The Strands code exists (`agent/khidki_agent/bedrock.py`) but has never completed a model call: Bedrock returns "Operation not allowed" on this account. Every answer so far is a template. |
| "Amazon Bedrock: language, never decisions" | Landing, "Built on AWS" | **FAIL as stated** | Same reason. Screenshot: `docs/screens/audit/local-landing-scroll-desktop-4.jpg`. |
| "Amazon Polly: Hindi voice" | Landing | **WARN: API only** | `GET /v1/rooms/6B/audio` works live (returns the Hindi text and a presigned S3 URL). No button in the UI calls it. |
| "Amazon EventBridge: the 6 AM plan" | Landing | PASS | Schedule `khidki-morning-plan`, `cron(0 6 * * ? *)`, `Asia/Kolkata`, ENABLED; planner Lambda invoked once in the last 48 h with 0 errors. |
| Benchmark table (65 → 17 minutes, 15 → 4 requests, PM 89% → 93%) | README, landing | PASS | `docs/benchmark.md`, `bench/results/summary.json`; labelled "simulation with real outdoor air, not a field trial". The landing page's "74%" is (65 − 17) / 65. |
| LocalStack instructions | README | WARN: not verified | Not run in this audit. The DynamoDB store is covered with moto in `tests/test_dynamo_store.py`. The README example also uses `ap-south-1`. |
| "Work in progress: see docs/SPEC.md for the plan" | README | WARN | `SPEC.md` still describes IoT Core, Cognito, AppSync, Transcribe and SES, all cut in `SCOPE.md`. A judge who follows the link will read features that do not exist. Fix: point to `SCOPE.md` and say what was cut. |

Features that exist only in text: Bedrock-phrased answers; the parent digest and `/lab` page (listed as
KEEP in `docs/SCOPE.md`, not built; `/lab` and `/parent/abc` render a blank page,
`docs/screens/audit/local-lab-tablet-light.jpg`).

Fix for the three FAIL/WARN claims: either get Bedrock unblocked and add the small "Ask" panel, or change
the wording to "Strands agent ready; on this account Bedrock is blocked, so answers come from verified
templates", and move Bedrock out of the "Built on AWS" grid.

---

## B. "What you build" rules

### 5. Git history: WARN (report only; do not rewrite)
- First commit: Thu 8 Oct 2026, 17:04 IST. Last commit: Sat 10 Oct 2026, 00:38 IST. 25 commits, one author.
  Author and committer dates match on every commit; nothing looks squashed or re-dated.
- No commit predates 8 Oct. **Please confirm the kickoff hour**: if the event opened after 17:04 IST on the
  8th, the first three commits are early.
- The first commit is the 1,034-line spec, and its own message says "plan written before kickoff". That is
  disclosed, which is the right way to handle it, but a judge will notice that the design predates the
  event.
- Cadence is bursty. Thu: 3 commits in 33 minutes (scaffold at 17:33, then all of the core science, 2,441
  lines, at 17:37). Fri: 17 commits between 20:24 and 23:59, several large ones a minute apart (22:00 to
  22:03, 23:47 to 23:59). Sat: 5 commits by 00:38. Then **no commit for 20 hours**. All 24 later commits
  reached GitHub in a single push on Sat evening.
- How a judge reads it: work was committed in batches rather than as it happened. It is not a rule breach,
  but it is weaker evidence of "built during the event" than a steady history.
- Fix: commit each remaining change separately from now on and push after each. Explain the batching in one
  honest sentence in the writeup. Do not touch existing history.

### 6. Old-project check: PASS, with one disclosure
An earlier Khidki prototype exists on this laptop (`~/Dev/untitled folder`, built before kickoff). Every
file in the repo was compared with the same-named file there (`difflib` similarity):

- No source file is a copy. Outside the four below, the highest similarity is 0.41 (a scenario YAML) and
  almost all Python and TypeScript files are under 0.30.
- `docs/SPEC.md`: 0.99. This is the pre-kickoff plan, committed and labelled as such.
- `core/khidki_core/policy/khidki.cedarschema`: 0.91, 911 bytes. The schema is written out in the spec, so
  both versions follow it.
- `web/index.html`: 0.91, 21 lines of Vite boilerplate and the font link. `web/src/main.tsx` 0.62 and
  `web/vite.config.ts` 0.61 are boilerplate too.
- The package layout and file names match the earlier prototype, because both follow the same spec.

How a judge reads it: same design, rewritten code. Fix: say exactly that in the writeup ("we planned before
kickoff and wrote the spec; all code was written during the event").

### 7. Credits and licences: WARN
| Check | Status | Evidence and fix |
|---|---|---|
| `docs/CREDITS.md` exists | PASS | Data, libraries, fonts and the AI tool are listed. |
| Table is well-formed | FAIL | Five library rows (Cedar, Strands, boto3, moto, Matplotlib) sit after the "AI coding tools" paragraph, outside any table, and the libraries section still says "Filled in as each library is added". Fix: move them into the table. |
| Every dependency credited | WARN | Missing: Powertools for AWS Lambda (MIT-0), AWS CDK and constructs (Apache-2.0), httpx (BSD-3), pre-commit (MIT), hatchling (MIT), Lighthouse (Apache-2.0, used for this audit). Also name Amazon Polly's Kajal voice as the audio source. |
| Open-Meteo / CAMS attribution visible in the UI | PASS | Landing footer, principal page (`School.tsx:78`), print page (`Print.tsx:53`), and `/v1/health`. |
| Attribution on the teacher screen | WARN | The teacher page shows outdoor AQI with no source line. Fix: one small line under the readouts, or accept it and rely on the landing and principal pages. |
| data.gov.in / CPCB | PASS (unused) | Credited, but no key is configured, so no CPCB data is shown. The UI says the forecast is uncorrected. |
| Research citations | WARN | `docs/physics.md` has no "(verify)" markers although `SCOPE.md` requires them on unconfirmed citations. Only Rawat et al. 2025 was confirmed against its DOI. Fix: mark Rawat and Kumar 2024, Allen 2016 and Persily and de Jonge 2017 "(verify)" or confirm each. |

### 8. AWS usage is real: PASS, except Bedrock
Checked against the deployed account (CloudFormation stack `Khidki`, `UPDATE_COMPLETE`, 46 resources) and
the code.

| Service or tool | Used in | Real? | How to show it on screen |
|---|---|---|---|
| AWS Step Functions | `infra/stacks/khidki_stack.py` (NudgeSM), `cloud/khidki_cloud/handlers.py` (`nudge_task`) | Yes: 7 executions, all SUCCEEDED, before this audit | Console graph view of one execution: IssueNudge (waiting for the tap) → WaitThenVerify → VerifyFromCO2 → Verified |
| AWS Lambda | 4 functions, Python 3.12 | Yes: 289 / 91 / 26 / 1 invocations in 48 h, 0 errors | Functions list, or the CloudWatch dashboard |
| Amazon API Gateway (HTTP API) | stack; `/v1/*` | Yes: all probed routes answer | The URL in the browser's network tab |
| Amazon DynamoDB | `services/khidki_services/dynamo.py` | Yes: table `Khidki`, 66 items, on-demand | Explore items: one ROOM partition with PLAN, NUDGE and READING rows |
| Amazon EventBridge Scheduler | stack | Yes: enabled, fired once | Schedule page showing 06:00 Asia/Kolkata |
| Amazon Polly | `handlers.py` `/audio` | Yes, API only | Needs a play button in the UI, otherwise show the S3 object |
| Amazon S3 | audio cache | Yes: private, encrypted, public access blocked | Bucket with `audio/*.mp3` |
| AWS Systems Manager Parameter Store | `runtime.ssm_param` | Yes: `/khidki/device_key`, `/khidki/admin_key` | Parameter list (values hidden) |
| AWS Amplify Hosting | `scripts/web_deploy.py` | Yes: site live over HTTPS | The live URL |
| Amazon CloudWatch | dashboard, 4 alarms, EMF metrics, log groups with 14-day retention | Yes | Dashboard |
| AWS CDK (open source) | `infra/` | Yes | `cdk deploy` output or the stack's resource list |
| Cedar (open source) | `core/khidki_core/policy/` | Yes: every activity decision carries policy ids | The principal page plus the `.cedar` file side by side |
| Powertools for AWS Lambda (open source) | `handlers.py` | Yes | Not worth screen time |
| Strands Agents (open source) | `agent/khidki_agent/bedrock.py` | **Code only**: never run against a model | Cannot be shown honestly until Bedrock is unblocked |
| Amazon Bedrock | same | **No**: blocked on this account | Cannot be shown |

---

## C. Prize eligibility

### 9. Open-source tool and/or deployed on AWS: PASS (both)
Cedar is used for real decisions and the stack is deployed. Strands should not be the tool you lead with,
because it has not run.

### 10. Build It path (fresh clone, no AWS account): PASS
Run in an empty directory on Sat 10 Oct:

| Step | Result |
|---|---|
| `git clone https://github.com/bhavya-jpg/khidki.git` | OK, 25 commits, 14 s |
| `python3 tasks.py setup` | OK in 3 s. Caveat: uv's package cache was warm on this laptop; a judge's first install will download about 100 packages. |
| `python3 tasks.py local partial_open` | OK. API on :8000 (`/v1/health` → `"mode":"local"`), web on :5173 (HTTP 200). `npm install` ran by itself. |
| Open `/teacher/6B` | OK: instruction, tap, verification all work (`audit-evidence/e2e-local-http.log`). |

Notes: the README says "Node 20+" and Python comes from `.python-version` through uv, so the system Python
(3.14 here) did not matter. `python tasks.py help` still lists five commands that print "Not built yet"
(`tasks.py:77-85`: provision-device, seed-demo, synth-phrases, demo-reset, arch-diagram). Fix: delete those
stubs.

### 11. Ship It path (live URL): WARN
| Check | Status | Evidence |
|---|---|---|
| Loads signed-out over HTTPS | PASS | `https://main.d3bl1gzeyloljx.amplifyapp.com/` 200 in 0.55 s; every route 200 in a fresh Playwright context. |
| No console errors | PASS | 0 console errors and 0 failed requests on `/`, `/teacher/6B`, `/school/dsv`, `/print/6B`, `/dev/window` (`docs/screens/audit/live-report.json`). |
| **Core flow works when a judge opens it** | **FAIL** | With no simulator running, the cloud clock keeps going but no readings arrive. At audit time the live teacher page said "No reading from the sensor for 12172 minutes" at simulated 19:47 (`docs/screens/audit/live-teacher-tablet-light.jpg`). A judge who clicks the link sees a dead classroom. |
| Principal override on the live site | **FAIL** | The web sends no passcode (`web/src/routes/School.tsx:165` posts only key, outdoor and reason), and the cloud requires `x-khidki-admin` (`handlers.py:120`). Live result: `401 Principal passcode required`. It works locally only because local mode has no check. |
| Write endpoints need a key | PASS / WARN | `POST /v1/ingest` without a key → 401. `POST /v1/sim/control` → 401. `POST /v1/schools/dsv/override` → 401. But `POST /v1/nudges/<id>/ack`, `POST /v1/rooms/<id>/replan` and `POST /v1/agent/ask` are open to anyone. Acceptable for a demo if said plainly. |
| Cost risk | WARN | Spend so far this month: $0.00 (Cost Explorer). Risks: no throttling on the HTTP API (`DefaultRouteSettings` has none), three open POST routes, and Lambdas sized at 1,769 MB. A script hitting `/replan` in a loop would burn credits. DynamoDB is on-demand; logs expire after 14 days; the S3 bucket has no lifecycle rule (tiny audio files, low risk). |
| **Budget alarm exists** | **FAIL** | `budgets:DescribeBudgets` → none. Cost Anomaly Detection monitors → 0. The four CloudWatch alarms have no actions, so nobody is told when they fire. Fix: add an AWS Budget (for example $20 with an email at 50% and 100%) and API throttling (for example 20 requests/s, burst 40). |

Live end-to-end run during the audit (simulator on this laptop posting to `/v1/ingest`, taps through the
API): see section 15.

---

## D. Judging criteria

### 12. Idea and Impact (Air track): 7 / 10
For: a real, narrow problem (the classroom window on a bad-air day) that sits squarely on the Air track:
indoor air, school safety on bad days, pollution exposure. The numbers are sourced and honestly labelled
as simulation on real outdoor data. The printable timetable means a school with no hardware still gets
something.

Against:
- The headline is CO₂ and fewer interruptions. On PM2.5 itself Khidki is slightly worse than the CO₂ alarm
  in the balanced setting (93% against 89% of an always-open room). An Air-track judge will ask "does it cut
  pollution exposure?", and the honest answer is "not without a purifier".
- No real person has used it: no teacher quote, no measured room. The real-room card was dropped because no
  data arrived by the 18:00 cut-off (correctly: never fake it).
- "What concretely changes for the people" is told in minutes above 1,500 ppm, not in a child's day.

Top three changes:
1. Open the video and writeup with the purifier-room result and the PM-weighted setting (matches the alarm
   on both PM2.5 and CO₂ with a third of the requests), and say the limitation in one sentence.
2. Get one real reaction: show the teacher screen to a single teacher or the DTU contact and quote them,
   labelled as one person's reaction.
3. State the impact per class: "48 fewer minutes a day of stuffy air for 44 children, 11 fewer
   interruptions for the teacher".

### 13. Built on AWS: 7 / 10
For: the Step Functions callback pattern (`waitForTaskToken` for the teacher's tap, then a timed wait, then
verification) is a use the service is actually good at, not decoration. Cedar decides real things and the
UI shows which policy fired. Everything is in CDK. Security basics are sound: the bucket is private and
encrypted, keys live in Parameter Store and are compared with `hmac.compare_digest`, IAM policies name
specific resources (table ARN, state machine ARN, two parameters, Nova models only), CORS allows only
localhost because the site proxies `/v1` on the same origin.

Against:
- Bedrock and Strands are claimed and not working.
- **No architecture diagram** anywhere outside the old spec (`grep -il mermaid README.md docs/*.md` finds
  only `SPEC.md`).
- No budget alarm, no throttling, alarms with no actions.
- IAM is broader than needed in places: the ingest and planner roles can read the admin key and start
  executions they never start; the API role has delete rights on the bucket.
- The README has no "Where AWS fits" section and no live URL.
- Hosting is in Sydney for a Delhi product. There is a good reason (the account's region lock), but it is
  only explained in `SCOPE.md`.

Top three changes:
1. Add a Mermaid architecture diagram and a "Where AWS fits" table to the README (reuse the table in
   section 8).
2. Add the budget and throttling to the CDK stack, and say so.
3. Either get Bedrock working or remove it from every claim.

### 14. Design and usability: 7 / 10
84 screenshots were taken with Playwright: every route at 1024×600, 390×844 and 1440×900, light and dark,
plus reduced motion, language toggled, keyboard focus, error routes and the landing page section by
section. Automated checks ran on each page (overflow, contrast, target size, labels, clipped text).

| Check | Status | Evidence |
|---|---|---|
| Teacher: would a first-time teacher know what to do? | PASS | One large Hindi instruction, a window picture, a countdown ring and two buttons. `local-teacher-phone-light.jpg`, `local-teacher-tablet-light.jpg`. |
| **Teacher: the reason line contradicts the instruction** | **FAIL** | Under "Open the road-side windows" the card says "सब ठीक है। जैसा है वैसा रहने दीजिए।" (All fine, keep things as they are). The print page has the same on its 07:50 row (`local-print-desktop-light.jpg`). Cause: `planning.py:73-74` labels any step equal to the one before it `KEEP_STEADY`, so after a re-plan the open action loses its real reason. |
| Principal: first-time walkthrough | WARN | Clear layout, policy ids and the number behind each decision. But a room at 1,714 ppm CO₂ carries the badge "All fine" (`local-school-tablet-light.jpg`), and Override fails on the live site (section 11). |
| Parent | FAIL | No parent page exists; `/parent/abc` is blank. |
| Finding your way around | WARN | The landing page links only to the teacher screen. Nothing links to the principal page or the printable timetable; a judge has to know the URLs. Unknown routes render a completely blank page (no 404). |
| Error state | WARN | An unknown room shows one line of English, "Can't reach Khidki: No room 9Z", with no way back (`local-teacher-unknown-room-tablet-light.jpg`). Local mode also answers 500 on `/v1/rooms/9Z/plan` (the cloud returns 404). |
| Loading, offline and stale states | PASS | "Loading…" in both languages; "No connection for N min. Last instruction shown"; "No reading from the sensor for N minutes" (`Teacher.tsx:83-190`). The poller keeps the last good value. |
| Hindi / English toggle | PASS | Works on all four pages; `<html lang>` follows it. Room names stay in Latin script ("Class 6B") on the Hindi principal page. |
| Devanagari clipping or overlap | PASS | No clipped Devanagari found by the automated check or by eye at any size. |
| Horizontal overflow | PASS | None on user-facing pages. `/dev/window` overflows by 15 px on a phone (developer page). |
| Contrast (WCAG AA) | WARN | Teacher and principal pages: 0 failures. Print page in dark mode: the Print button is 1.85:1. Landing hero: one paragraph at 4.19:1 against 4.5 (Lighthouse). |
| Keyboard focus | PASS | 2 px outline plus a 6 px amber ring on every page (`*-tablet-light-focus.jpg`). |
| Touch targets (44 px) | WARN | Teacher page: all pass. Principal page: "Override" links are 59×34, room links 74×32, "Show as table" 95×34, "DoE circulars" 68×15. |
| Landmarks and tables | WARN | Landing has no `<main>`; the print table's cells have no header association (Lighthouse). |
| Reduced motion | PASS | Honoured in `base.css:82`, `AirWindow.tsx:30`, `Landing.tsx:47`. |
| Built for a cheap tablet and flaky Wi-Fi | WARN | JavaScript is small (84 KB gzipped) and the page polls and degrades well. But the Devanagari font alone is **709 KB** (variable weight and width axes from Google Fonts), about 70% of the page, and it is fetched from a third-party CDN. No offline cache. |

Lighthouse 13.5 on the live site, mobile emulation (`audit-evidence/lighthouse-summary.txt`):

| Route | Performance | Accessibility | Best practices | SEO | LCP |
|---|---|---|---|---|---|
| `/` | 67 | 95 | 100 | 100 | 7.7 s |
| `/teacher/6B` | 79 | 100 | 100 | 100 | 3.6 s |
| `/school/dsv` | 91 | 100 | 100 | 100 | 3.1 s |
| `/print/6B` | 87 | 93 | 100 | 100 | 3.4 s |

Top three changes:
1. Fix the contradictory reason line (it is on the two most-filmed screens).
2. Cut the font weight: request only the weights used and drop the width axis, or self-host a subset.
3. Add navigation between the three roles, a real 404, and fix Override on the live site.

### 15. Execution: 6 / 10
**Tests and checks.** `pytest`: **125 passed, 0 failed** (70 s). `ruff check` and `ruff format --check`:
clean on 83 files. `mypy core`: no issues in 15 files. `tsc` and `vite build`: clean. GitHub Actions run
38061962156 on `main`: success.

**End-to-end flow, local** (fresh clone, `partial_open`, taps sent through the HTTP API;
`audit-evidence/e2e-local-http.log`):

```
07:45 issued  "Open the road-side windows"  → tapped → verifying
07:48 verified.   Then at once: issued "Close the windows" → tapped → verified 07:51
07:51 issued  "Open the road-side windows" again → tapped → verified 07:55
08:35 issued  "Open both sides" → tapped (the simulator opens only one side) → 08:38 "verified"
```

Two defects show in that log, and both reproduce in-process (`audit-evidence/partial-open-repro.log`):

1. **Open, close, open in six minutes.** With the engine ticking every 5 to 15 simulated seconds (which is
   what local mode does), 6B is asked to open at 07:45, close at 07:48 and open again at 07:51.
   That is half the day's budget of six in the first six minutes, in both `partial_open` and
   `severe_morning`. With 30-second ticks (what the tests use) it does not happen, which is why the tests
   are green.
2. **The one-side catch is timing-dependent.** Asked for both sides while only one opened: caught (verdict
   partial → follow-up → verified at λ 8.27) with 5, 10 and 30-second ticks; **missed** with 15-second ticks,
   in the local HTTP run and on the live stack. Three of six. When missed, the evidence says "air data inconclusive … went by the teacher's tap",
   yet the screen says "CO₂ की रेखा से पक्का हुआ" (confirmed from the CO₂ curve). That is the centrepiece of
   the demo, and in the missed case the on-screen sentence is not true.

**End-to-end flow, deployed stack:** taps for 6B sent through the live API while the simulator on
this laptop posted readings to `/v1/ingest` (`audit-evidence/e2e-live-with-taps.log`,
`audit-evidence/stepfunctions-executions.txt`):

```
07:46 issued "Open the road-side windows" → tapped → verifying → 07:49 verified
      Step Functions: IssueNudge → TeacherTapped → WaitThenVerify → VerifyFromCO2 → AirChanged → Verified
08:35 issued "Open both sides" → tapped (the simulator opens only one side) → 08:39 "verified"
      Step Functions: IssueNudge → TeacherTapped → WaitThenVerify → VerifyFromCO2 → AirChanged → Verified
```

So plan → instruction → tap → verification → re-plan works on AWS, with a real Step Functions execution
behind each instruction. A first live run without taps exercised the other branches: NoTapInTime →
FollowUpNudge → NotFollowed_Replanned. The flip-flop did not appear in the two live runs. But **the
one-side catch was missed on the live stack too**: the execution went straight to Verified.

One more finding from the live runs:

3. **Resetting the demo mid-flight leaves a red execution.** Starting a scenario while an execution was
   waiting to verify produced the only FAILED execution on the account: `KeyError '6B-1763436357'` at
   `handlers.py:323`, because the reset had deleted the nudge. Every retake of the video will risk one, and
   it shows in the console and in the `NudgeSMFailed` alarm.

After the audit the state machine has 21 executions: 20 SUCCEEDED, 1 FAILED. The live site was left at the
end of that run and is stale again.

**Feature status**

| Feature | Status | Note |
|---|---|---|
| Physics twin, dose, AQI and GRAP, optimizer | WORKS | Unit tests |
| Daily plan and 5-minute re-plan | WORKS | Local and cloud |
| Teacher screen: instruction, tap, "can't right now" | WORKS | Local and live |
| Verification from the CO₂ curve | WORKS | λ fitted and compared in every run |
| One-side follow-up | **PARTIAL** | 3 of 6 runs; missed on the live stack |
| Calm plan (no flip-flop) | **PARTIAL** | Open, close, open at 07:45 to 07:51 locally; not seen in two live runs |
| Reason text under the instruction | **BROKEN** | "All fine" under an open instruction |
| Cedar activity decisions on the principal page | WORKS | Local and live |
| Principal override with audit log | **PARTIAL** | Works locally; 401 on the live site |
| Printable timetable | WORKS | Apart from the reason text on one row |
| NudgeSM on Step Functions | WORKS | 20 of 21 executions SUCCEEDED; the one failure came from a demo reset |
| 06:00 plan by EventBridge Scheduler | WORKS | Fired once, 0 errors |
| Live site without a simulator running | **BROKEN** | Stale for 12,172 simulated minutes |
| Resetting the demo between takes | **PARTIAL** | Fails any execution that is mid-flight |
| Ask Khidki | **PARTIAL** | API and templates only; no UI; Bedrock blocked |
| Polly Hindi audio | **PARTIAL** | API only; no button |
| CPCB bias correction | PARTIAL | Off (no key); labelled "uncorrected" |
| Benchmark and chart | WORKS | Reproducible seeds |
| Hindi / English, offline and stale banners | WORKS | |
| `/lab`, `/parent`, real-room card | MISSING | Not built |

Recommendation: do not demo anything marked PARTIAL or BROKEN as it stands. Fix the three that sit on the
teacher's screen (reason text, flip-flop, one-side catch) because that screen is the product. For the rest,
fix or cut: Override (fix, 30 minutes, or leave it out of the video), Ask Khidki and audio (add small UI or
drop every mention), `/lab` and `/parent` (cut, and say so in `SCOPE.md`).

Top three changes:
1. Make verification honest and repeatable: when the fit is inconclusive, wait and fit again instead of
   trusting the tap, and never print "confirmed from the CO₂ curve" for a tap-only result.
2. Add a minimum hold after a verified change so the plan cannot reverse within a few minutes.
3. Keep the live site alive without a laptop (a small scheduled simulator Lambda), or state on the landing
   page that the live classroom runs only during demos.

### 16. Demo video: 2 / 10 today (nothing exists)
No script and no recording. Proposed 2:40 script, using only what works once the MUST fixes are in:

| Time | Scene | On screen | AWS shown |
|---|---|---|---|
| 0:00–0:15 | The problem | Landing hero, toggle Shut / Open: "Shut: CO₂ passes 2,000 ppm in one period. Open: the smog comes in." | |
| 0:15–0:30 | Who it's for, what it does | "Khidki tells the teacher the exact minute, then checks the air." | |
| 0:30–0:50 | 6 AM plan | Principal page: PE moved indoors, "S2 … forecast 97 µg/m³", next to the Cedar policy file | EventBridge schedule, Cedar |
| 0:50–1:25 | Instruction, tap, verify | Teacher tablet: instruction appears, tap "I've opened them", ring counts down, ✓ | Step Functions execution graph, split screen, waiting on the task token and then moving to Verified |
| 1:25–1:55 | Only one side opened | Follow-up: "Open the corridor side too", second tap, verified | Same execution taking the FollowUpNudge branch |
| 1:55–2:10 | Can't right now: too cold | Tap the reason; the ribbon re-plans | DynamoDB item for the constraint |
| 2:10–2:25 | Proof | Benchmark: 65 → 17 minutes, 15 → 4 requests, with "simulation on 48 real Delhi days, not a field trial" on screen | CloudWatch dashboard, 2 seconds |
| 2:25–2:40 | No hardware, and close | Printable timetable; the architecture diagram; "Built with Claude Code" | Diagram |

Leave out Ask Khidki, audio and Override unless they are fixed and visible in the UI. Say "simulated
classroom, real outdoor air" out loud once in the first 30 seconds.

---

## E. Extra prizes

### 17. Blog: FAIL (not started), with strong material
`docs/blog.md` does not exist. `docs/LEARNINGS.md` has 1,786 words of "what fought back" and is most of a
blog already. The strongest stories, in order:

1. **"The verification hold was a region lock all along"**: a new AWS account, a managed policy that denies
   everything outside the home region, and a Delhi product shipped from Sydney.
2. **"The tracer-gas trick has blind spots, and the simulator found them"**: using children's breath as the
   tracer gas, and what happens in an empty room near outdoor CO₂. This audit adds a third blind spot.
3. **"The benchmark said trade-off, not win"**: choosing the honest headline.
4. **"The smallest μ that meets the budget still chatters"**: the optimizer story, with the flip-flop found
   today as its sequel.
5. **"Cedar returns which policy decided, if you ask for annotations"**: a short, useful Cedar tip.
6. **"A 43 KB/s network decides the Python version"**: a good opening anecdote.

Fix: about 900 words built on stories 1 to 3, the architecture diagram, two screenshots, published on AWS
Builder Center and linked in the submission.

### 18. Amazon fast-track signal
What a reviewer would notice: 125 tests including the Step Functions path and the Lambda handlers under
moto; state transitions written as pure functions and driven the same way locally and by Step Functions; a
safety model in policy code with the policy id shown to the user; a number-fidelity guard on agent answers;
a reproducible benchmark that reports its own weak result; honest labels on every simulated screen;
pre-commit hooks and CI; infrastructure as code; a "what fought back" log.

Gaps that weaken it: the flakiness found here sits exactly where the tests use a coarser clock than
production; no test runs the engine at the production tick rate; no budget or throttling; alarms that
notify nobody; ingest averages 1.6 s and peaks at 5.7 s; no architecture diagram, runbook or safety note;
bursty commit history.

---

## F. Summary

| Criterion | Score / status | Biggest gap |
|---|---|---|
| A1 Repository readiness | PASS | Stale `.env.example` |
| A2 Demo video plan | **FAIL** | No script, no video |
| A3 Writeup | **FAIL** | Not written |
| A4 Feature honesty | WARN | Bedrock and Strands claimed but not working; Ask and audio have no UI |
| B5 Git history | WARN | Batched commits, one push, 20-hour gap; confirm the kickoff hour |
| B6 Old-project check | PASS | Spec predates kickoff (disclosed); code is rewritten |
| B7 Credits | WARN | Malformed table, six libraries missing, no "(verify)" marks |
| B8 AWS usage is real | PASS | Except Bedrock |
| C9 Eligibility | PASS | Cedar plus a deployed stack |
| C10 Build It (fresh clone) | PASS | Dead stub commands in `tasks.py` |
| C11 Ship It (live URL) | WARN | Live page frozen without a simulator; Override 401; no budget alarm |
| D12 Idea and Impact | 7 / 10 | PM2.5 benefit is not the headline; no real user |
| D13 Built on AWS | 7 / 10 | No architecture diagram; Bedrock claim; no budget or throttling |
| D14 Design and usability | 7 / 10 | Contradictory reason line; 709 KB font; no navigation or 404 |
| D15 Execution | 6 / 10 | One-side catch is timing-dependent; open-close-open flip-flop |
| D16 Demo video | 2 / 10 | Does not exist |
| E17 Blog | **FAIL** | Not started |
| E18 Fast-track signal | Good | Tests run on a coarser clock than production |

### Prioritised fix list
Ordered by impact on the judging score divided by hours. Submission blockers first.

| # | Fix | Tag | Hours | Raises |
|---|---|---|---|---|
| 1 | Write `docs/demo-script.md` (2:40, section 16) | MUST | 0.5 | A2, D16 |
| 2 | Write `docs/submission.md` (about 250 words; AWS, AI tool, honest limits, the pre-kickoff spec, why Sydney) | MUST | 0.5 | A3 |
| 3 | Rewrite the README: live URLs, architecture diagram (Mermaid), "Where AWS fits" table, limitations, point to `SCOPE.md`, remove "work in progress", fix the region | MUST | 0.7 | A4, D13 |
| 4 | Fix the reason line so an open instruction never says "All fine" (teacher card and print page) | MUST | 0.3 | D14, D15 |
| 5 | Honest claims: reword or remove Bedrock and Strands on the landing page and README | MUST | 0.2 | A4, D13 |
| 6 | Fix `docs/CREDITS.md` (table, six libraries, Polly) and add "(verify)" marks in `physics.md` | MUST | 0.3 | B7 |
| 7 | Verification: on an inconclusive fit, wait and fit again; never show "confirmed from the CO₂ curve" for a tap-only result; add a test at the production tick rate | MUST | 1.0 | D15 |
| 8 | Minimum hold after a verified change, so no open-close-open (engine layer, not the optimizer); test at the production tick rate | MUST | 1.0 | D15, D12 |
| 9 | Budget alarm (a $1 budget with an email alert; AWS Budgets itself is free) and API throttling in the CDK stack; redeploy | MUST | 0.4 | C11, D13 |
| 10 | Record and upload the video (you) | MUST | 1.5 | A2, D16 |
| 11 | Commit and push after every fix from here on | MUST | 0 | B5 |
| 12 | Override on the live site: ask for the principal passcode in the form and send it; read the cloud's error message | SHOULD | 0.5 | C11, D15 |
| 13 | Demo reset: end in-flight executions cleanly (the verify task returns "gone" instead of raising when its nudge was wiped), so retakes leave no red execution | SHOULD | 0.3 | D13, D16 |
| 14 | Live site: a plain "the live classroom runs during demos; watch the video" notice on the landing page. The scheduled simulator Lambda is ruled out by the zero-spend rule (it would pass the 4,000 free Step Functions transitions a month within days) | SHOULD | 0.1 | C11 |
| 15 | Write and publish the blog from `LEARNINGS.md` | SHOULD | 0.8 | E17 |
| 16 | Font diet: only the weights used, no width axis | SHOULD | 0.4 | D14 |
| 17 | Navigation between teacher, principal and print pages; a 404 page; a friendlier unknown-room state | SHOULD | 0.5 | D14 |
| 18 | Audio button on the teacher card (the endpoint is live) | SHOULD | 0.4 | D13, A4 |
| 19 | Small accessibility fixes: print button in dark mode, `<main>` on landing, table headers, 44 px targets on the principal page, "All fine" badge on a 1,700 ppm room | SHOULD | 0.5 | D14 |
| 20 | Tidy: `tasks.py` stubs, `.env.example`, stale YAML comment, mark `/lab` and `/parent` as cut in `SCOPE.md` | SHOULD | 0.2 | A4, C10 |
| 21 | One real teacher reaction, quoted and labelled (you) | SHOULD | 1.0 | D12 |
| 22 | Bedrock Support case and Ask panel | SKIP | n/a | Bedrock has no free allowance; under the zero-spend rule the agent stays on templates and the claims are reworded (fix 5) |
| 23 | `/lab` and `/parent` pages | SKIP | 3.0 | Past the freeze; the landing page already carries the results |
| 24 | Real-room CO₂ card | SKIP | n/a | The 18:00 cut-off passed with no data; never fake it |
| 25 | Tighten IAM per function; SNS actions on alarms; auth on ack and replan | SKIP | 1.5 | Say it in the limitations instead |
| 26 | Replace the bisection optimizer with fixed μ | SKIP | 2.0 | The benchmark depends on the current one |

MUST items total about 6.4 hours including the recording. Items 7 and 8 change behaviour after your 21:00
feature freeze; they are bug fixes to features already built, but that is your call.

### Zero-spend rule (added after the audit, Sat 10 Oct, 21:30 IST)
The owner's rule is that nothing may be charged. Checked the same evening:

- `freetier:GetAccountPlanState` reports the account plan as **PAID** with **$0 remaining credits**, not the
  Free plan with credits that the sign-up email described. This must be confirmed in the Billing console.
- Cost Explorer returns no rows at all for 8 to 10 Oct, not even the usage that certainly happened, so its
  "$0" is missing data, not proof.
- Usage this month from CloudWatch metrics: Lambda 1,201 invocations and 426 GB-seconds (always-free: 1M and
  400,000); Step Functions 21 executions, about 250 transitions (always-free: 4,000 a month); 4 custom
  metrics, 4 alarms, 1 dashboard (always-free: 10, 10, 3). Not covered by an always-free allowance: 1,128
  HTTP API calls, 6,774 DynamoDB on-demand write units and 41,820 read units, 57 Polly characters, a few KB
  in S3 and Amplify. At list prices that is roughly one to two US cents so far.
- Consequences for the fix list: item 9 uses a $1 budget, item 14 becomes a notice instead of an always-on
  simulator, item 22 is skipped, and the stack should be destroyed (`cdk destroy`) once judging is over.

### Do not touch
These work and should stay frozen:

- `core/khidki_core/` physics, dose, AQI, GRAP, optimizer and inference maths (the benchmark numbers depend
  on them; fixes 7 and 8 belong in `services/khidki_services/engine.py`).
- `core/khidki_core/policy/khidki.cedar` and the schema.
- The NudgeSM state machine definition and the CDK stack's structure (deployed, with successful executions
  on every branch). Fix 9 only adds resources.
- `bench/` and `docs/benchmark.md`.
- The DynamoDB store and key layout.
- The AirWindow renderer and the design tokens.
- CI, the pre-commit hooks, and **all existing git history**.
