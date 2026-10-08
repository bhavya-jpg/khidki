"""Finite-horizon dynamic program over (CO₂, PM2.5, previous action) with a teacher-attention budget.

Stage cost per step (normalised per day so the weights read as intended):

    α · PMdose / PMdose_always_open
  + (1 − α) · CO₂points / (occupied minutes at 1,500 ppm)
  + β · cold / cold_always_open
  + μ · [action changed]

μ is found by bisection in log space: the smallest switch penalty whose plan asks for at most
`max_changes` changes (a Lagrangian relaxation of the attention budget).

Speed trick: given the action, CO₂ and PM evolve independently, so bilinear interpolation of the value
function is two 1-D lookups. The previous action enters only through μ, so the continuation term is computed
once per action, then V[prev] = min(Q[prev], min_a Q[a] + μ).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from khidki_core import dose
from khidki_core.physics import (
    ActionArrays,
    DriveSeries,
    FloatArray,
    IntArray,
    SimResult,
    co2_coeffs,
    co2_source_ppm_per_h,
    pm_coeffs,
    relax,
    simulate,
)
from khidki_core.schemas import Kpis, RoomParams, Window

CO2_BAND_EDGES = (800.0, 1000.0, 1500.0, 2000.0)
N_CO2_BANDS = len(CO2_BAND_EDGES) + 1
BIG = 1e6  # finite stand-in for "forbidden" so interpolation never meets inf·0

BoolArray = NDArray[np.bool_]
MaskFn = Callable[[DriveSeries, ActionArrays], BoolArray]
"""Returns allowed[t, co2_band, action] for the horizon."""


def co2_band(co2: FloatArray | float) -> IntArray:
    """0: <800, 1: <1,000, 2: <1,500, 3: <2,000, 4: ≥2,000 ppm."""
    return np.asarray(np.digitize(co2, CO2_BAND_EDGES), dtype=np.int64)


@dataclass(frozen=True)
class Grid:
    co2_lo: float = 400.0
    co2_hi: float = 4000.0
    co2_step: float = 25.0
    pm_lo: float = 0.0
    pm_hi: float = 400.0
    pm_step: float = 2.0

    @property
    def co2(self) -> FloatArray:
        return np.arange(self.co2_lo, self.co2_hi + self.co2_step / 2, self.co2_step)

    @property
    def pm(self) -> FloatArray:
        return np.arange(self.pm_lo, self.pm_hi + self.pm_step / 2, self.pm_step)


def _interp_weights(x: FloatArray, lo: float, step: float, n: int) -> tuple[IntArray, FloatArray]:
    f = (np.asarray(x, dtype=np.float64) - lo) / step
    i0 = np.clip(np.floor(f), 0, n - 2).astype(np.int64)
    w = np.clip(f - i0, 0.0, 1.0)
    return i0, w


@dataclass(frozen=True)
class CostConfig:
    alpha: float = 0.5
    beta: float = 0.3
    ir_m3_h: float = dose.DEFAULT_IR_M3_H


@dataclass(frozen=True)
class Norms:
    pm: float
    co2: float
    cold: float


def compute_norms(
    params: RoomParams,
    drive: DriveSeries,
    aa: ActionArrays,
    co2_0: float,
    pm_0: float,
    ir_m3_h: float = dose.DEFAULT_IR_M3_H,
) -> Norms:
    """Per-horizon normalisers. PM by an always-open room; CO₂ by "every occupied minute at 1,500 ppm"
    (1 point per minute; see docs/LEARNINGS.md); cold by always-open."""
    open_idx = int(np.argmax(np.where(~aa.purifier_on, aa.lam, -1)))
    n = len(drive)
    sim = simulate(params, drive, aa, np.full(n, open_idx), co2_0, pm_0)
    kids = drive.children_present
    pm_norm = float(np.sum(sim.pm_mean * kids) * ir_m3_h * drive.dt_h)
    occ_min = float(kids.sum() * drive.dt_min)
    cold_norm = float(
        np.sum(dose.cold_rate(aa.open_fraction[open_idx], drive.temp_out) * kids) * drive.dt_min
    )
    return Norms(pm=max(pm_norm, 1.0), co2=max(occ_min, 1.0), cold=max(cold_norm, max(occ_min, 1.0)))


@dataclass
class _StepPhysics:
    """Coefficients for one time step, per action."""

    a_c: FloatArray
    b_c: FloatArray
    a_p: FloatArray
    b_p: FloatArray
    stage_const: FloatArray  # cold term, per action


def _step_physics(
    params: RoomParams, drive: DriveSeries, aa: ActionArrays, cfg: CostConfig, norms: Norms, t: int
) -> _StepPhysics:
    src = float(co2_source_ppm_per_h(drive.n_children[t], drive.n_adults[t], params))
    a_c, b_c = co2_coeffs(aa.lam, float(drive.co2_out[t]), src)
    a_p, b_p = pm_coeffs(aa.lam, aa.pen, aa.q_eff_m3_h, float(drive.pm_out[t]), params)
    kids = float(drive.children_present[t])
    cold = (
        cfg.beta
        / norms.cold
        * dose.cold_rate(aa.open_fraction, float(drive.temp_out[t]))
        * drive.dt_min
        * kids
    )
    return _StepPhysics(a_c=a_c, b_c=b_c, a_p=a_p, b_p=b_p, stage_const=np.asarray(cold, dtype=np.float64))


def _stage_terms(
    c_mean: FloatArray, p_mean: FloatArray, cfg: CostConfig, norms: Norms, drive: DriveSeries, t: int
) -> tuple[FloatArray, FloatArray]:
    kids = float(drive.children_present[t])
    pm_term = cfg.alpha / norms.pm * p_mean * cfg.ir_m3_h * drive.dt_h * kids
    co2_term = (1 - cfg.alpha) / norms.co2 * dose.co2_points_rate(c_mean) * drive.dt_min * kids
    return co2_term, pm_term


@dataclass
class DPSolution:
    values: list[NDArray[np.float32]]
    """values[t] has shape (A, Nc, Np): cost-to-go from step t given the previous action. len = T + 1."""
    mu: float


def solve_dp(
    params: RoomParams,
    drive: DriveSeries,
    aa: ActionArrays,
    cfg: CostConfig,
    norms: Norms,
    allowed: BoolArray,
    mu: float,
    grid: Grid,
) -> DPSolution:
    cg, pg = grid.co2, grid.pm
    nc, np_, na, nt = len(cg), len(pg), len(aa), len(drive)
    bands = co2_band(cg)
    values: list[NDArray[np.float32]] = [np.zeros((na, nc, np_), dtype=np.float32) for _ in range(nt + 1)]
    q = np.empty((na, nc, np_), dtype=np.float32)
    for t in range(nt - 1, -1, -1):
        sp = _step_physics(params, drive, aa, cfg, norms, t)
        v_next = values[t + 1]
        for a in range(na):
            c_end, c_mean = relax(cg, sp.a_c[a], sp.b_c[a], drive.dt_h)
            p_end, p_mean = relax(pg, sp.a_p[a], sp.b_p[a], drive.dt_h)
            co2_term, pm_term = _stage_terms(c_mean, p_mean, cfg, norms, drive, t)
            ic, wc = _interp_weights(c_end, grid.co2_lo, grid.co2_step, nc)
            ip, wp = _interp_weights(p_end, grid.pm_lo, grid.pm_step, np_)
            # Separable bilinear interpolation: along PM, then along CO₂.
            vn = v_next[a]
            wp32 = wp.astype(np.float32)
            vp = vn[:, ip] + wp32 * (vn[:, ip + 1] - vn[:, ip])
            wc32 = wc.astype(np.float32)[:, None]
            cont = vp[ic] + wc32 * (vp[ic + 1] - vp[ic])
            qa = q[a]
            np.add(cont, (co2_term + sp.stage_const[a]).astype(np.float32)[:, None], out=qa)
            qa += pm_term.astype(np.float32)[None, :]
            qa[~allowed[t, bands, a], :] = BIG
        q_min = q.min(axis=0)
        values[t] = np.minimum(q, q_min[None] + np.float32(mu))
    return DPSolution(values=values, mu=mu)


def _bilinear(v: NDArray[np.float32], c: float, p: float, grid: Grid) -> float:
    nc, np_ = v.shape
    ic, wc = _interp_weights(np.array([c]), grid.co2_lo, grid.co2_step, nc)
    ip, wp = _interp_weights(np.array([p]), grid.pm_lo, grid.pm_step, np_)
    i, j, x, y = int(ic[0]), int(ip[0]), float(wc[0]), float(wp[0])
    return float(
        (1 - x) * ((1 - y) * v[i, j] + y * v[i, j + 1]) + x * ((1 - y) * v[i + 1, j] + y * v[i + 1, j + 1])
    )


def rollout(
    params: RoomParams,
    drive: DriveSeries,
    aa: ActionArrays,
    cfg: CostConfig,
    norms: Norms,
    allowed: BoolArray,
    sol: DPSolution,
    grid: Grid,
    co2_0: float,
    pm_0: float,
    prev: int,
) -> IntArray:
    """Greedy one-step lookahead on the exact state using the DP value function."""
    c, p = co2_0, pm_0
    chosen = np.empty(len(drive), dtype=np.int64)
    for t in range(len(drive)):
        sp = _step_physics(params, drive, aa, cfg, norms, t)
        band = int(co2_band(c))
        best_a, best_q = prev, np.inf
        nexts: dict[int, tuple[float, float]] = {}
        # Try "keep" first so ties prefer not bothering the teacher.
        order = [prev] + [a for a in range(len(aa)) if a != prev]
        for a in order:
            if not allowed[t, band, a]:
                continue
            c_end, c_mean = relax(c, sp.a_c[a], sp.b_c[a], drive.dt_h)
            p_end, p_mean = relax(p, sp.a_p[a], sp.b_p[a], drive.dt_h)
            co2_term, pm_term = _stage_terms(c_mean, p_mean, cfg, norms, drive, t)
            qv = float(co2_term + pm_term) + float(sp.stage_const[a])
            qv += _bilinear(sol.values[t + 1][a], float(c_end), float(p_end), grid)
            qv += 0.0 if a == prev else sol.mu
            if qv < best_q - 1e-12:
                best_a, best_q = a, qv
            nexts[a] = (float(c_end), float(p_end))
        if best_a not in nexts:  # nothing allowed: hold (should not happen; closing is always allowed)
            c_end, _ = relax(c, sp.a_c[best_a], sp.b_c[best_a], drive.dt_h)
            p_end, _ = relax(p, sp.a_p[best_a], sp.b_p[best_a], drive.dt_h)
            nexts[best_a] = (float(c_end), float(p_end))
        chosen[t] = best_a
        c, p = nexts[best_a]
        prev = best_a
    return chosen


def allow_all(drive: DriveSeries, aa: ActionArrays) -> BoolArray:
    return np.ones((len(drive), N_CO2_BANDS, len(aa)), dtype=np.bool_)


@dataclass
class OptResult:
    action_idx: IntArray
    mu: float
    budget_binding: bool
    sim: SimResult
    kpis: Kpis
    n_solves: int
    seconds: float
    norms: Norms
    allowed: BoolArray = field(repr=False)


def optimize(
    params: RoomParams,
    drive: DriveSeries,
    aa: ActionArrays,
    co2_0: float,
    pm_0: float,
    prev_idx: int,
    cfg: CostConfig | None = None,
    max_changes: int = 6,
    allowed: BoolArray | None = None,
    grid: Grid | None = None,
    mu_floor: float = 2e-3,
) -> OptResult:
    """Plan the rest of the day. Respects the action mask and the attention budget.

    `mu_floor` is the minimum price of interrupting the teacher (0.2% of a day's normalised cost). Without
    it the plan chatters (open, close, open within 20 minutes) for gains under 1% of PM dose."""
    t0 = time.perf_counter()
    cfg = cfg or CostConfig()
    grid = grid or Grid()
    allowed = allowed if allowed is not None else allow_all(drive, aa)
    # Never leave a (step, CO₂ band) with no legal action: fall back to closing, which policy always permits.
    closed = [i for i, a in enumerate(aa.actions) if a.window == Window.CLOSED]
    allowed = allowed.copy()
    empty = ~allowed.any(axis=2)
    allowed[empty, closed[0]] = True
    norms = compute_norms(params, drive, aa, co2_0, pm_0, cfg.ir_m3_h)
    n_solves = 0

    def attempt(mu: float) -> tuple[IntArray, int]:
        nonlocal n_solves
        n_solves += 1
        sol = solve_dp(params, drive, aa, cfg, norms, allowed, mu, grid)
        idx = rollout(params, drive, aa, cfg, norms, allowed, sol, grid, co2_0, pm_0, prev_idx)
        return idx, dose.count_changes(idx, prev_idx)

    best_idx, changes = attempt(mu_floor)
    best_mu, binding = mu_floor, False
    if changes > max_changes:
        binding = True
        lo, hi = mu_floor, 0.02
        hi_idx, hi_changes = attempt(hi)
        while hi_changes > max_changes and hi < 10.0:
            lo, hi = hi, hi * 4
            hi_idx, hi_changes = attempt(hi)
        best_idx, best_mu = hi_idx, hi
        for _ in range(6):
            mid = float(np.sqrt(lo * hi))
            mid_idx, mid_changes = attempt(mid)
            if mid_changes <= max_changes:
                hi, best_idx, best_mu = mid, mid_idx, mid
            else:
                lo = mid
    sim = simulate(params, drive, aa, best_idx, co2_0, pm_0)
    kpis = dose.compute_kpis(drive, sim, aa, best_idx, prev_idx, cfg.ir_m3_h)
    return OptResult(
        action_idx=best_idx,
        mu=best_mu,
        budget_binding=binding,
        sim=sim,
        kpis=kpis,
        n_solves=n_solves,
        seconds=time.perf_counter() - t0,
        norms=norms,
        allowed=allowed,
    )
