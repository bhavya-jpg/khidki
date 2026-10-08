# The physics behind Khidki

Khidki models a classroom as one well-mixed box of air. Two numbers describe it: indoor CO₂ `C` (ppm) and
indoor PM2.5 `P` (µg/m³). The teacher controls the window `w` (closed, cracked, one side open, both sides
open) and, if the room has one, an air purifier `a`.

```
dC/dt = λ(w)·(C_out − C) + S
dP/dt = p(w)·λ(w)·P_out − (λ(w) + k + q(a)/V)·P + E/V
```

Code: [`core/khidki_core/physics.py`](../core/khidki_core/physics.py). Tests: [`tests/test_physics.py`](../tests/test_physics.py).

## Parameters

| Symbol | Meaning | Default | Source / note |
|---|---|---|---|
| `λ(w)` | air changes per hour | closed 0.7, cracked 2.5, one side open 6, both sides (cross-ventilation) 10 h⁻¹ | typical naturally ventilated classrooms; replaced nightly by the room fingerprint |
| `S` | CO₂ source, ppm/h | `N·G·3.6e6 / V` | `G` = 0.0035 L/s per seated 10 to 13 year old, 0.0052 L/s per adult (approximate, after Persily & de Jonge 2017, *Indoor Air* 27:868) |
| `V` | room volume | 166 m³ (8.0 × 6.5 × 3.2 m) | demo room |
| `N` | people in the room | 44 children + 1 teacher | from the timetable; 0 when the class is outside |
| `C_out` | outdoor CO₂ | 450 ppm | or Open-Meteo `carbon_dioxide` |
| `p(w)` | PM2.5 penetration | closed 0.8, cracked 0.95, open 1.0 | LBNL infiltration study (P ≈ 0.97); Beijing window-crack study (P ≈ 0.93) |
| `k` | PM2.5 deposition | 0.2 h⁻¹ | homes ~0.08 to 0.10 h⁻¹; classrooms higher with occupancy and resuspension |
| `q(a)` | purifier clean-air delivery | 350 m³/h × 0.8 effectiveness | typical room purifier |
| `E` | indoor PM2.5 source | 0 | option for chalk dust and resuspension |

## The dilemma, in numbers

All of these are regression tests in `tests/test_physics.py`.

| Situation (44 children, outdoor PM2.5 250 µg/m³) | CO₂ | Indoor PM2.5 |
|---|---|---|
| CO₂ source | +3,450 ppm per hour | |
| Windows shut, steady state | ~5,380 ppm | ~156 µg/m³ |
| Windows shut, after one 40-minute period from 600 ppm | ~2,380 ppm | |
| One side open, steady state | ~1,030 ppm | ~242 µg/m³ |
| Shut, with a purifier running | (as shut) | ~54 µg/m³ |

Shut, the children's own breath takes the room past 2,000 ppm within a period. Open, the room fills with
smog. The purifier helps only with the windows shut, and then CO₂ climbs.

One more consequence: holding 44 children under 1,500 ppm needs about 3.3 air changes per hour. At that
ventilation, indoor PM is already about 94% of what a fully open room gets. So in a room *without* a
purifier, Khidki's lever is mostly **timing**: purge during recess, close when outdoor PM spikes, open
when it dips. The big PM lever is a purifier plus shut windows, and Khidki coordinates the two.

## Exact discretisation

Both equations have the form `dx/dt = b − a·x`. With inputs held constant over a step `Δt`:

```
x(t+Δt) = b/a + (x − b/a)·e^(−a·Δt)
mean of x over the step = b/a + (x − b/a)·(1 − e^(−a·Δt)) / (a·Δt)
```

CO₂: `a = λ`, `b = λ·C_out + S`. PM: `a = λ + k + q/V`, `b = p·λ·P_out + E/V`. As `a → 0` the code falls
back to the linear limit. Planning uses `Δt` = 5 minutes, the simulator 30 seconds.

## Exposure metrics

Code: [`core/khidki_core/dose.py`](../core/khidki_core/dose.py).

- **PM2.5 dose per child** = Σ P · IR · Δt while children are in the room. IR = 0.5 m³/h for a seated
  child (US EPA *Exposure Factors Handbook*, ch. 6). Headline claims are relative (%), so they don't depend
  on IR.
- **Minutes above 1,000 and 1,500 ppm** while occupied.
- **CO₂ discomfort points** per occupied minute: 0 below 1,000 ppm, rising to 1 at 1,500, to 4 at 2,000,
  then +10 per extra 1,000 ppm.
- **Cold exposure** per minute: open fraction (closed 0, cracked 0.3, one side 0.6, both 1) × degrees
  below 18 °C outside.
- **Teacher attention**: the number of window or purifier changes the plan asks for.

CO₂ is treated as a ventilation and stuffiness indicator with a cognition-motivated penalty, not a medical
claim. Allen et al. (2016, *EHP*) found cognitive scores ~15% lower at ~945 ppm and ~50% lower at
~1,400 ppm than at ~550 ppm, but other studies find task-dependent effects.

## The optimizer

Code: [`core/khidki_core/optimizer.py`](../core/khidki_core/optimizer.py).

A finite-horizon dynamic program from now to the end of the school day, in 5-minute steps, over a grid of
CO₂ (400 to 4,000 ppm, 25-ppm bins) × PM2.5 (0 to 400 µg/m³, 2-µg bins) × previous action. Stage cost:

```
α · PMdose / PMdose(always open)
+ (1 − α) · CO₂points / (occupied minutes × 1)        ← "the whole day at 1,500 ppm"
+ β · cold / cold(always open)
+ μ · [the teacher is asked to change something]
```

Profiles: Balanced α = 0.5, Lungs-first α = 0.7 (sensitive students or severe days), Focus-first
α = 0.35 (exam days); β = 0.3.

**Attention budget.** A teacher should be interrupted at most 6 times a day. Instead of adding a
change-counter to the state, Khidki uses a Lagrangian relaxation: it searches for the smallest switch
penalty μ whose plan needs ≤ 6 changes (bisection in log space).

**Why it's fast.** Given the action, CO₂ and PM evolve independently. Bilinear interpolation of the value
function then needs only 1-D lookups in each axis. The previous action matters only through μ, so the
continuation is computed once per action, and `V[prev] = min(Q[prev], min_a Q[a] + μ)`.

**Policy mask.** Before solving, Cedar decides which actions are allowed for each step and CO₂ band
(< 800, < 1,000, < 1,500, < 2,000, ≥ 2,000 ppm). The DP never considers a forbidden action.

## Window inference: the children are the tracer gas

Code: [`core/khidki_core/inference.py`](../core/khidki_core/inference.py).

Over 3 to 5 minutes with known occupancy, CO₂ follows `C(t) = C_ss + (C₀ − C_ss)·e^(−λt)` with
`C_ss = C_out + S/λ`. For every candidate λ the amplitude has a closed-form least-squares solution, so a
fine 1-D search finds λ. Its nearest fingerprint state (in log λ) is the inferred window, with a confidence
score and hysteresis. This is the tracer-gas decay idea (ASTM E741), using the children's exhaled CO₂.

**Verification.** After "open both sides", Khidki expects λ near the room's both-sides rate. ≥ 70% of it:
verified. Clearly above "cracked" but short of that: partial ("only one side seems open"). Otherwise: not
changed.

## Room fingerprint

Code: [`core/khidki_core/calibration.py`](../core/khidki_core/calibration.py).

Each night Khidki splits the day into segments of constant window state, purifier and occupancy, fits λ per
segment from CO₂, and takes the median per window state. With λ fixed, it grid-searches closed-window PM
penetration, deposition `k` and purifier effectiveness against the indoor PM sensor. Parameters are
accepted only within physical bounds (λ 0.1 to 20 h⁻¹, p 0.3 to 1.0, k 0.02 to 1.5 h⁻¹), with λ increasing
from closed to open and a PM fit R² ≥ 0.5. Otherwise yesterday's values stay.

## Indian AQI and GRAP

Code: [`core/khidki_core/aqi.py`](../core/khidki_core/aqi.py), [`grap.py`](../core/khidki_core/grap.py).

CPCB National AQI PM2.5 sub-index (2014, 24-hour): Good 0 to 30 → 0 to 50; Satisfactory 31 to 60 → 51 to
100; Moderate 61 to 90 → 101 to 200; Poor 91 to 120 → 201 to 300; Very poor 121 to 250 → 301 to 400;
Severe 250+ → 401 to 500. The table leaves Severe open-ended; Khidki takes 380 µg/m³ as AQI 500 and caps
there.

Indicative GRAP stage from city AQI: I 201 to 300, II 301 to 400, III 401 to 450, IV > 450. It is labelled
*indicative*. The official stage is whatever CAQM has ordered, and the principal can set it. Khidki
reminds and links to DoE circulars; it never enforces or contradicts an official order.

## Limitations

- One well-mixed zone: no gradients inside the room.
- Default parameters are literature-based approximations until the room is fingerprinted.
- The CAMS outdoor forecast is ~45 km resolution and under-predicts Delhi peaks; live mode bias-corrects
  against the nearest CPCB station.
- Not a medical device, and not a field-validated trial.

## References

- Rawat N., Kumar P., et al. (2025). IoT-driven acoustic and visual CO₂ feedback in classrooms. *Sci. Total
  Environ.* 980:179543.
- Rawat N., Kumar P. (2024). Air purifier and scheduled natural ventilation in a near-highway school.
  *J. Building Eng.* 86:108813.
- Allen J.G. et al. (2016). Associations of cognitive function scores with CO₂, ventilation and VOC
  exposures. *Environ. Health Perspect.*
- Persily A., de Jonge L. (2017). Carbon dioxide generation rates for building occupants. *Indoor Air*
  27(5):868–879.
- US EPA *Exposure Factors Handbook*, chapter 6 (inhalation rates).
- CPCB National Air Quality Index (2014); CAQM GRAP (revised Dec 2024).
