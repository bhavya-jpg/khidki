"""Room fingerprint: fit each room's own air-change rates, PM penetration and deposition from a day of
telemetry (system identification).

1. Split the day into segments with constant window state, purifier and occupancy.
2. Fit λ per segment from the CO₂ curve (inference.fit_ach, known source from occupancy). The median per
   window state becomes the fingerprint.
3. With λ fixed, grid-search PM penetration (closed), deposition k and purifier effectiveness to minimise
   squared error of the simulated indoor PM against the sensor.

Parameters are only accepted inside physical bounds; otherwise yesterday's are kept and the fit is flagged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from khidki_core.inference import fit_ach
from khidki_core.physics import FloatArray, co2_source_ppm_per_h
from khidki_core.schemas import WINDOW_ORDER, RoomParams, Window

LAMBDA_BOUNDS = (0.1, 20.0)
PEN_BOUNDS = (0.3, 1.0)
K_BOUNDS = (0.02, 1.5)
MIN_SEGMENT_SAMPLES = 6
MAX_SEGMENT_RMSE_PPM = 60.0


@dataclass(frozen=True)
class Telemetry:
    """A day of readings at (roughly) regular intervals."""

    t_h: FloatArray
    co2: FloatArray
    pm: FloatArray
    pm_out: FloatArray
    co2_out: FloatArray
    n_children: FloatArray
    n_adults: FloatArray
    window: tuple[Window, ...]
    """Known window state per sample (window contact, the plan log, or inferred)."""
    purifier_on: NDArray[np.bool_]


@dataclass(frozen=True)
class Segment:
    start: int
    stop: int
    window: Window
    purifier_on: bool
    lam: float
    rmse: float


@dataclass
class Fingerprint:
    lam: dict[Window, float]
    pen_closed: float
    deposition_per_h: float
    purifier_effectiveness: float
    co2_r2: float
    pm_r2: float
    pm_rmse: float
    n_segments: int
    accepted: bool
    notes: list[str] = field(default_factory=list)


def segments(tel: Telemetry) -> list[tuple[int, int]]:
    """Runs of constant (window, purifier, occupancy)."""
    keys = list(
        zip(tel.window, tel.purifier_on.tolist(), tel.n_children.tolist(), tel.n_adults.tolist(), strict=True)
    )
    runs: list[tuple[int, int]] = []
    start = 0
    for i in range(1, len(keys) + 1):
        if i == len(keys) or keys[i] != keys[start]:
            runs.append((start, i))
            start = i
    return runs


def fit_segments(tel: Telemetry, params: RoomParams) -> list[Segment]:
    out: list[Segment] = []
    for a, b in segments(tel):
        if b - a < MIN_SEGMENT_SAMPLES:
            continue
        src = float(co2_source_ppm_per_h(tel.n_children[a], tel.n_adults[a], params))
        fit = fit_ach(tel.t_h[a:b], tel.co2[a:b], float(np.mean(tel.co2_out[a:b])), src)
        if fit.rmse > MAX_SEGMENT_RMSE_PPM:
            continue
        out.append(Segment(a, b, tel.window[a], bool(tel.purifier_on[a]), fit.lam, fit.rmse))
    return out


def _co2_r2(tel: Telemetry, segs: list[Segment], lam: dict[Window, float], params: RoomParams) -> float:
    """R² of the CO₂ curve over the fitted segments, using the fingerprint λ (not each segment's own)."""
    sse = sst = 0.0
    for s in segs:
        src = float(co2_source_ppm_per_h(tel.n_children[s.start], tel.n_adults[s.start], params))
        c_out = float(np.mean(tel.co2_out[s.start : s.stop]))
        t = tel.t_h[s.start : s.stop] - tel.t_h[s.start]
        z = tel.co2[s.start : s.stop]
        css = c_out + src / lam[s.window]
        e = np.exp(-lam[s.window] * t)
        amp = float(np.sum((z - css) * e) / np.sum(e * e))
        sse += float(np.sum((z - css - amp * e) ** 2))
        sst += float(np.sum((z - z.mean()) ** 2))
    return 1.0 - sse / sst if sst > 0 else 0.0


def _simulate_pm_grid(
    tel: Telemetry,
    lam_per_sample: FloatArray,
    pen_per_sample: FloatArray,
    closed: NDArray[np.bool_],
    pen_closed: FloatArray,
    k: FloatArray,
    eff: FloatArray,
    params: RoomParams,
) -> FloatArray:
    """Indoor PM for many candidate (pen_closed, k, eff) at once. Returns (G, n)."""
    n = len(tel.t_h)
    g = len(pen_closed)
    p = np.full(g, float(tel.pm[0]))
    out = np.empty((g, n))
    out[:, 0] = p
    q_nom = params.purifier_cadr_m3_h / params.volume_m3
    for i in range(1, n):
        dt = float(tel.t_h[i] - tel.t_h[i - 1])
        j = i - 1  # inputs held over [t_{i-1}, t_i)
        lam = lam_per_sample[j]
        pen = np.where(closed[j], pen_closed, pen_per_sample[j])
        a = lam + k + (q_nom * eff if tel.purifier_on[j] else 0.0)
        b = pen * lam * tel.pm_out[j]
        xss = b / a
        p = xss + (p - xss) * np.exp(-a * dt)
        out[:, i] = p
    return out


def fit_fingerprint(tel: Telemetry, prior: RoomParams) -> Fingerprint:
    notes: list[str] = []
    segs = fit_segments(tel, prior)
    lam = dict(prior.lam)
    for w in WINDOW_ORDER:
        vals = [s.lam for s in segs if s.window == w]
        if vals:
            lam[w] = float(np.median(vals))
        else:
            notes.append(f"no clean {w.value} segment; kept prior λ")
    co2_r2 = _co2_r2(tel, segs, lam, prior) if segs else 0.0

    # PM: λ fixed per sample from the fingerprint.
    lam_s = np.array([lam[w] for w in tel.window])
    pen_s = np.array([prior.pen[w] for w in tel.window])
    closed = np.array([w == Window.CLOSED for w in tel.window])
    pens = np.linspace(PEN_BOUNDS[0], PEN_BOUNDS[1], 36)
    ks = np.geomspace(K_BOUNDS[0], K_BOUNDS[1], 40)
    effs = np.linspace(0.3, 1.0, 15) if tel.purifier_on.any() else np.array([prior.purifier_effectiveness])
    pp, kk, ee = (x.ravel() for x in np.meshgrid(pens, ks, effs, indexing="ij"))
    sim = _simulate_pm_grid(tel, lam_s, pen_s, closed, pp, kk, ee, prior)
    sse = np.sum((sim - tel.pm[None, :]) ** 2, axis=1)
    best = int(np.argmin(sse))
    sst = float(np.sum((tel.pm - tel.pm.mean()) ** 2))
    pm_r2 = 1.0 - float(sse[best]) / sst if sst > 0 else 0.0
    pm_rmse = float(np.sqrt(sse[best] / len(tel.pm)))

    accepted = bool(segs)
    if not segs:
        notes.append("no usable CO₂ segments")
    for w, v in lam.items():
        if not LAMBDA_BOUNDS[0] <= v <= LAMBDA_BOUNDS[1]:
            accepted = False
            notes.append(f"λ {w.value} = {v:.2f} outside physical bounds")
    ordered = [lam[w] for w in WINDOW_ORDER]
    if any(b <= a for a, b in pairwise(ordered)):
        accepted = False
        notes.append("λ not increasing from closed to open")
    if pm_r2 < 0.5:
        accepted = False
        notes.append(f"PM fit too weak (R² {pm_r2:.2f})")

    return Fingerprint(
        lam={w: round(v, 3) for w, v in lam.items()},
        pen_closed=round(float(pp[best]), 3),
        deposition_per_h=round(float(kk[best]), 3),
        purifier_effectiveness=round(float(ee[best]), 3),
        co2_r2=round(co2_r2, 3),
        pm_r2=round(pm_r2, 3),
        pm_rmse=round(pm_rmse, 2),
        n_segments=len(segs),
        accepted=accepted,
        notes=notes,
    )


def apply_fingerprint(params: RoomParams, fp: Fingerprint) -> RoomParams:
    """Tomorrow's twin. Rejected fingerprints change nothing."""
    if not fp.accepted:
        return params
    pen = dict(params.pen)
    pen[Window.CLOSED] = fp.pen_closed
    return params.model_copy(
        update={
            "lam": dict(fp.lam),
            "pen": pen,
            "deposition_per_h": fp.deposition_per_h,
            "purifier_effectiveness": fp.purifier_effectiveness,
        }
    )
