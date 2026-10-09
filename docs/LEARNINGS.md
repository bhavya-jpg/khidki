# What fought back

A running log of surprises, wrong assumptions and fixes, written as they happen. It feeds the Builder
Center blog post.

## Thu 8 Oct 2026 (kickoff)

### A 43 KB/s network decides the Python version
The venue network measured about 43 KB/s to PyPI, so `uv sync` sat resolving for 10 minutes. The local uv
cache already held wheels for Python 3.12 (which the spec asks for, and Lambda supports), so the project
pins 3.12 and the first sync ran with `--offline` in seconds. Lesson: on a slow link, resolve and download
once, then work offline.

### GitHub over HTTPS
The machine had no SSH key registered with GitHub, so the first push failed. The repo uses HTTPS with the
GitHub CLI as its credential helper (`git config credential.helper '!gh auth git-credential'`).

### The CO₂ normaliser has to be "a day at 1,500 ppm", not "an always-closed room"
The spec normalises the CO₂ term by an always-closed room's discomfort points. On a severe day that
baseline sits near 5,000 ppm, and the points grow by 10 per 1,000 ppm above 2,000, so the normaliser is
huge and keeping the class at 1,700 ppm all morning looks almost free. (This was one of the lessons from
the pre-event practice prototype, which is not in this repo.) Khidki normalises by "every occupied minute
at 1,500 ppm" (1 point per minute), so 1% of an always-open PM dose trades against 1% of a day at 1,500 ppm.

### Separable interpolation made the DP 2.4× faster
Given the action, CO₂ and PM evolve independently, so bilinear interpolation of the value function is two
1-D passes (along PM, then along CO₂) instead of four 2-D gathers. In float32 that took one DP solve from
0.51 s to about 0.22 s for a purifier room (8 actions), and the whole attention-budget search from 4.5 s to
1.9 s. Same plans, bit for bit on the test day.

### The smallest μ that meets the budget still chatters
Bisecting for the *smallest* switch penalty that fits 6 changes gave plans like "open both at 07:50, close
at 08:00, open both at 08:05, open one at 08:10": legal, and maddening for a teacher. Those flips bought
under 1% of PM dose. A floor on μ (each interruption costs 0.2% of the day's normalised cost) turns that
into "open one side at 07:45, both at 08:45" for +0.5% PM. Budget and floor together: never more than 6,
and never a change that isn't worth it.

### A purifier room's PM lever is bounded by CO₂
44 children need about 3.3 air changes per hour to stay under 1,500 ppm. With a 350 m³/h purifier at that
ventilation, indoor PM is still about 64% of outdoor, against about 84% fully open with the purifier on.
So "cut PM by 30% against always-open + purifier" was an impossible test. Khidki gets 17% with zero minutes
above 1,500 ppm. The test now checks the physics-backed claim, and the benchmark will report it honestly.

### Small spec adaptations
- Four window states, not three: closed, cracked, one side open (6 h⁻¹), both sides open (10 h⁻¹). The
  partial-open story needs "one side" and "both sides" to be different states.
- 35-minute periods, so that 8 periods, a 20-minute assembly at 07:30 and a 10:10 to 10:40 recess fit a
  07:30 to 13:00 day on a 5-minute grid.
- One extra reason code, `AIR_REFRESHED` ("CO₂ is down, close to keep the smog out"), for closing after a
  purge, which none of the spec's codes described.

## Fri 9 Oct 2026

### A new AWS account is locked for a while, even after "your account is now active"
`aws configure` worked and `sts get-caller-identity` returned the user, but every service call (DynamoDB,
Lambda, IoT, S3, CloudFormation) failed with "explicit deny in a service control policy" from an
AWS-owned organisation, and Bedrock said "Your account is currently being verified". The denies outlasted
the activation email. The IAM user was fine (AdministratorAccess); the block sits above IAM. The spec's
advice, confirmed: create the AWS account days early.

### The Free plan quietly changes the AI plan
On the AWS Free plan, Bedrock global and geographic cross-Region inference are not allowed, and in
ap-south-1 Nova models are reachable *only* through `apac.` or `global.` inference profiles. Polly was
explicitly denied by the account's service control policy. us-east-1 serves `amazon.nova-lite-v1:0`
in-region (ON_DEMAND), which is the fallback to test once the account unlocks.

### CAMS reads Delhi low
The 48 cached school days (15 Oct to 19 Dec 2025, East Delhi) have a median 24-hour CAMS PM2.5 of
91 µg/m³ and a maximum of 178. CPCB stations were reporting "Very poor" and "Severe" through November.
CAMS global is ~45 km and smooths out the city. Replay days are labelled "CAMS model values, uncorrected";
live mode bias-corrects against the nearest CPCB station. Relative results (Khidki vs baselines) are less
sensitive to the scale than absolute doses.

### `&&` only guards the line it's on
A commit went in with three lint errors because `git commit` sat on its own line after a failing
`ruff check && ...` chain. Fixed in the next commit; checks and commit now run under `set -e`.

### The tracer-gas trick has blind spots, and the simulator found them
Running a whole simulated morning surfaced three verification bugs the unit tests didn't:
1. **Closing near outdoor CO₂.** Right after closing, indoor CO₂ is only ~200 ppm above outdoor. The
   slope is dominated by the children's breath, and a sensor's ±3% calibration error shifts the fitted λ
   enough to read "closed" as "cracked". Khidki marked two real closings as "not changed". Fix: when an
   instruction makes the room *less* open, verify against the boundary with the next more-open state, and
   treat closed and cracked as one class. What matters is that the room is no longer open.
2. **Direction matters.** "Go from both sides to one side" passed as verified while both sides were still
   open, because the check only asked "is λ at least 70% of the target?". Verification now takes the
   previous state.
3. **An empty room at outdoor CO₂ says nothing.** During PE the class was outside; Khidki asked to close the
   windows (nobody there) and "verified" it from a flat line. Now nudges only go out while the class is in
   the room or just leaving, and an empty room near outdoor CO₂ is "inconclusive".

### The attention budget leaked in the live loop
Each re-plan got "6 minus instructions already issued". With 0 left, the bisection can't find a 0-change
plan when CO₂ is climbing, and fell back to a plan with changes, so a 7th instruction went out. Now the
optimizer holds the current state when the budget can't be met, and the engine refuses to issue past it.
