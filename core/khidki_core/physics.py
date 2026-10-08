"""Well-mixed single-zone box model of a classroom (docs/physics.md).

    dC/dt = λ(w)·(C_out − C) + S_co2
    dP/dt = p(w)·λ(w)·P_out − (λ(w) + k + q(a)/V)·P + E/V

Both are of the form dx/dt = b − a·x. With constant inputs over a step we use the exact solution
x(t+Δt) = b/a + (x − b/a)·exp(−a·Δt), never Euler.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from khidki_core.schemas import WINDOW_ORDER, Action, Purifier, RoomParams, Window

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def co2_source_ppm_per_h(
    n_children: FloatArray | float,
    n_adults: FloatArray | float,
    params: RoomParams,
) -> FloatArray:
    """CO₂ source in ppm/h: N·G [L/s] × 3.6 [m³/h per L/s] / V [m³] × 1e6."""
    litres_per_s = (
        np.asarray(n_children, dtype=np.float64) * params.gen_child_lps
        + np.asarray(n_adults, dtype=np.float64) * params.gen_adult_lps
    )
    return litres_per_s * 3.6e6 / params.volume_m3


def relax(
    x0: FloatArray | float, a: FloatArray | float, b: FloatArray | float, dt_h: float
) -> tuple[FloatArray, FloatArray]:
    """Exact step of dx/dt = b − a·x over dt_h hours. Returns (x at end, time-mean of x over the step).

    Safe as a → 0 (falls back to the linear limit)."""
    x0 = np.asarray(x0, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    adt = a * dt_h
    small = adt < 1e-9
    safe_a = np.where(small, 1.0, a)
    decay = np.exp(-adt)
    # (1 − e^{−aΔt}) / (aΔt), → 1 as aΔt → 0
    frac = np.where(small, 1.0, -np.expm1(-adt) / np.where(small, 1.0, adt))
    xss = b / safe_a
    x_end = np.where(small, x0 + b * dt_h, xss + (x0 - xss) * decay)
    x_mean = np.where(small, x0 + b * dt_h / 2.0, xss + (x0 - xss) * frac)
    return x_end, x_mean


@dataclass(frozen=True)
class DriveSeries:
    """Exogenous inputs on a regular time grid. Element i applies over [t_min[i], t_min[i] + dt_min)."""

    t_min: IntArray
    dt_min: int
    pm_out: FloatArray
    co2_out: FloatArray
    temp_out: FloatArray
    n_children: FloatArray
    n_adults: FloatArray

    def __post_init__(self) -> None:
        n = len(self.t_min)
        for name in ("pm_out", "co2_out", "temp_out", "n_children", "n_adults"):
            if len(getattr(self, name)) != n:
                raise ValueError(f"{name} has length {len(getattr(self, name))}, expected {n}")

    def __len__(self) -> int:
        return len(self.t_min)

    @property
    def dt_h(self) -> float:
        return self.dt_min / 60.0

    @property
    def children_present(self) -> NDArray[np.bool_]:
        return self.n_children > 0

    def slice(self, start: int, stop: int | None = None) -> DriveSeries:
        s = slice(start, stop)
        return DriveSeries(
            t_min=self.t_min[s],
            dt_min=self.dt_min,
            pm_out=self.pm_out[s],
            co2_out=self.co2_out[s],
            temp_out=self.temp_out[s],
            n_children=self.n_children[s],
            n_adults=self.n_adults[s],
        )

    def resample(self, dt_min: int) -> DriveSeries:
        """Finer grid: occupancy held per step, outdoor values linearly interpolated."""
        if self.dt_min % dt_min:
            raise ValueError("new step must divide the old one")
        k = self.dt_min // dt_min
        t_new = np.arange(self.t_min[0], self.t_min[-1] + self.dt_min, dt_min, dtype=np.int64)

        def lin(x: FloatArray) -> FloatArray:
            return np.asarray(np.interp(t_new, self.t_min, x), dtype=np.float64)

        return DriveSeries(
            t_min=t_new,
            dt_min=dt_min,
            pm_out=lin(self.pm_out),
            co2_out=lin(self.co2_out),
            temp_out=lin(self.temp_out),
            n_children=np.repeat(self.n_children, k),
            n_adults=np.repeat(self.n_adults, k),
        )


@dataclass(frozen=True)
class ActionArrays:
    """Per-action physical coefficients, aligned with an action list."""

    actions: tuple[Action, ...]
    lam: FloatArray
    pen: FloatArray
    q_eff_m3_h: FloatArray
    open_fraction: FloatArray
    window_idx: IntArray
    purifier_on: NDArray[np.bool_]

    def __len__(self) -> int:
        return len(self.actions)

    def index(self, action: Action) -> int:
        return self.actions.index(action)


def action_space(params: RoomParams) -> tuple[Action, ...]:
    """All actions available in this room. Purifier actions only if the room has one."""
    purifier_states = (Purifier.OFF, Purifier.ON) if params.has_purifier else (Purifier.OFF,)
    return tuple(Action(window=w, purifier=a) for a in purifier_states for w in WINDOW_ORDER)


def action_arrays(params: RoomParams, actions: tuple[Action, ...] | None = None) -> ActionArrays:
    actions = actions if actions is not None else action_space(params)
    q = params.purifier_cadr_m3_h * params.purifier_effectiveness
    return ActionArrays(
        actions=actions,
        lam=np.array([params.lam[a.window] for a in actions], dtype=np.float64),
        pen=np.array([params.pen[a.window] for a in actions], dtype=np.float64),
        q_eff_m3_h=np.array([q if a.purifier == Purifier.ON else 0.0 for a in actions], dtype=np.float64),
        open_fraction=np.array([params.open_fraction[a.window] for a in actions], dtype=np.float64),
        window_idx=np.array([WINDOW_ORDER.index(a.window) for a in actions], dtype=np.int64),
        purifier_on=np.array([a.purifier == Purifier.ON for a in actions], dtype=np.bool_),
    )


def co2_coeffs(
    lam: FloatArray | float, c_out: FloatArray | float, source_ppm_h: FloatArray | float
) -> tuple[FloatArray, FloatArray]:
    lam = np.asarray(lam, dtype=np.float64)
    return lam, lam * c_out + source_ppm_h


def pm_coeffs(
    lam: FloatArray | float,
    pen: FloatArray | float,
    q_eff_m3_h: FloatArray | float,
    p_out: FloatArray | float,
    params: RoomParams,
) -> tuple[FloatArray, FloatArray]:
    lam = np.asarray(lam, dtype=np.float64)
    a = lam + params.deposition_per_h + np.asarray(q_eff_m3_h) / params.volume_m3
    b = np.asarray(pen) * lam * p_out + params.indoor_pm_source_ug_h / params.volume_m3
    return a, b


@dataclass(frozen=True)
class SimResult:
    co2: FloatArray
    """CO₂ at step boundaries, length T+1 (ppm)."""
    pm: FloatArray
    """Indoor PM2.5 at step boundaries, length T+1 (µg/m³)."""
    co2_mean: FloatArray
    """Time-mean CO₂ over each step, length T."""
    pm_mean: FloatArray


def simulate(
    params: RoomParams,
    drive: DriveSeries,
    aa: ActionArrays,
    action_idx: IntArray | list[int],
    co2_0: float,
    pm_0: float,
) -> SimResult:
    """Run the twin open-loop under a fixed action sequence."""
    idx = np.asarray(action_idx, dtype=np.int64)
    n = len(drive)
    if len(idx) != n:
        raise ValueError(f"need {n} actions, got {len(idx)}")
    src = co2_source_ppm_per_h(drive.n_children, drive.n_adults, params)
    a_c, b_c = co2_coeffs(aa.lam[idx], drive.co2_out, src)
    a_p, b_p = pm_coeffs(aa.lam[idx], aa.pen[idx], aa.q_eff_m3_h[idx], drive.pm_out, params)
    co2 = np.empty(n + 1)
    pm = np.empty(n + 1)
    co2_mean = np.empty(n)
    pm_mean = np.empty(n)
    co2[0], pm[0] = co2_0, pm_0
    for i in range(n):
        c_end, c_avg = relax(co2[i], a_c[i], b_c[i], drive.dt_h)
        p_end, p_avg = relax(pm[i], a_p[i], b_p[i], drive.dt_h)
        co2[i + 1], co2_mean[i] = float(c_end), float(c_avg)
        pm[i + 1], pm_mean[i] = float(p_end), float(p_avg)
    return SimResult(co2=co2, pm=pm, co2_mean=co2_mean, pm_mean=pm_mean)


def steady_state(
    params: RoomParams,
    window: Window,
    purifier: Purifier,
    p_out: float,
    c_out: float = 450.0,
    n_children: float | None = None,
    n_adults: float | None = None,
) -> tuple[float, float]:
    """Steady-state (CO₂, PM2.5) for constant conditions. Used in docs and sanity tests."""
    kids = params.students if n_children is None else n_children
    adults = params.adults if n_adults is None else n_adults
    aa = action_arrays(params, (Action(window=window, purifier=purifier),))
    src = co2_source_ppm_per_h(kids, adults, params)
    a_c, b_c = co2_coeffs(aa.lam[0], c_out, src)
    a_p, b_p = pm_coeffs(aa.lam[0], aa.pen[0], aa.q_eff_m3_h[0], p_out, params)
    return float(b_c / a_c), float(b_p / a_p)
