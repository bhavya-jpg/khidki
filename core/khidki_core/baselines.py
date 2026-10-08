"""Comparison policies, run closed-loop on the same twin and outdoor series as Khidki.

1. ALWAYS_CLOSED
2. ALWAYS_OPEN (both sides)
3. CO2_ALARM: open at > 1,500 ppm, close at < 1,000 ppm, 2-minute reaction, 70% compliance per alarm
4. TEMPERATURE_TEACHER: windows open when it is ≥ 22 °C outside, shut otherwise (what the 2025 Delhi
   classroom study observed teachers doing)
5. KHIDKI: follows a plan, with the same compliance model as the alarm for fairness

In rooms with a purifier, every baseline runs it whenever children are in the room.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from khidki_core import dose
from khidki_core.physics import (
    ActionArrays,
    DriveSeries,
    IntArray,
    SimResult,
    co2_coeffs,
    co2_source_ppm_per_h,
    pm_coeffs,
    relax,
)
from khidki_core.schemas import Action, Kpis, Purifier, RoomParams, Window


class Policy(Protocol):
    name: str

    def reset(self, rng: np.random.Generator) -> None: ...

    def act(
        self, i: int, co2: float, pm: float, drive: DriveSeries, aa: ActionArrays, current: int
    ) -> int: ...


def _idx(aa: ActionArrays, window: Window, purifier_on: bool) -> int:
    want = Action(window=window, purifier=Purifier.ON if purifier_on else Purifier.OFF)
    if want in aa.actions:
        return aa.index(want)
    return aa.index(Action(window=window, purifier=Purifier.OFF))


@dataclass
class Fixed:
    name: str
    window: Window

    def reset(self, rng: np.random.Generator) -> None:
        pass

    def act(self, i: int, co2: float, pm: float, drive: DriveSeries, aa: ActionArrays, current: int) -> int:
        return _idx(aa, self.window, bool(drive.children_present[i]))


@dataclass
class TemperatureTeacher:
    name: str = "TEMPERATURE_TEACHER"
    open_at_c: float = 22.0

    def reset(self, rng: np.random.Generator) -> None:
        pass

    def act(self, i: int, co2: float, pm: float, drive: DriveSeries, aa: ActionArrays, current: int) -> int:
        w = Window.OPEN_BOTH if drive.temp_out[i] >= self.open_at_c else Window.CLOSED
        return _idx(aa, w, bool(drive.children_present[i]))


@dataclass
class _Compliance:
    """A teacher who acts on a request with probability `p` after a delay, and is asked again every
    `recheck_min` minutes if they didn't."""

    p: float = 0.7
    delay_min: float = 2.0
    recheck_min: float = 10.0
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(0))
    _target: int | None = None
    _due_at: float = 0.0
    _will_do: bool = False

    def reset(self, rng: np.random.Generator) -> None:
        self.rng, self._target = rng, None

    def request(self, target: int, now_min: float, current: int) -> int:
        if target == current:
            self._target = None
            return current
        if target != self._target:
            self._target = target
            self._will_do = bool(self.rng.random() < self.p)
            self._due_at = now_min + (self.delay_min if self._will_do else self.recheck_min)
        if now_min >= self._due_at:
            if self._will_do:
                self._target = None
                return target
            self._will_do = bool(self.rng.random() < self.p)
            self._due_at = now_min + (self.delay_min if self._will_do else self.recheck_min)
        return current


@dataclass
class Co2Alarm:
    name: str = "CO2_ALARM"
    open_above: float = 1500.0
    close_below: float = 1000.0
    teacher: _Compliance = field(default_factory=_Compliance)
    _want_open: bool = False

    def reset(self, rng: np.random.Generator) -> None:
        self.teacher.reset(rng)
        self._want_open = False

    def act(self, i: int, co2: float, pm: float, drive: DriveSeries, aa: ActionArrays, current: int) -> int:
        if co2 > self.open_above:
            self._want_open = True
        elif co2 < self.close_below:
            self._want_open = False
        kids = bool(drive.children_present[i])
        want = _idx(aa, Window.OPEN_BOTH if self._want_open else Window.CLOSED, kids)
        # The purifier part of the action follows occupancy without asking the teacher.
        cur_window = aa.actions[current].window
        current_adj = _idx(aa, cur_window, kids)
        return self.teacher.request(want, float(drive.t_min[i]), current_adj)


@dataclass
class FollowPlan:
    """Khidki's instructions, followed with a compliance model. `plan` is per step of the drive."""

    plan: IntArray
    name: str = "KHIDKI"
    teacher: _Compliance = field(default_factory=lambda: _Compliance(p=1.0, delay_min=0.0))

    def reset(self, rng: np.random.Generator) -> None:
        self.teacher.reset(rng)

    def act(self, i: int, co2: float, pm: float, drive: DriveSeries, aa: ActionArrays, current: int) -> int:
        return self.teacher.request(int(self.plan[i]), float(drive.t_min[i]), current)


def standard_baselines(compliance: float = 0.7) -> list[Policy]:
    return [
        Fixed("ALWAYS_CLOSED", Window.CLOSED),
        Fixed("ALWAYS_OPEN", Window.OPEN_BOTH),
        Co2Alarm(teacher=_Compliance(p=compliance)),
        TemperatureTeacher(),
    ]


@dataclass(frozen=True)
class PolicyRun:
    name: str
    action_idx: IntArray
    sim: SimResult
    kpis: Kpis


def run_policy(
    params: RoomParams,
    drive: DriveSeries,
    aa: ActionArrays,
    policy: Policy,
    co2_0: float,
    pm_0: float,
    initial: int = 0,
    seed: int = 0,
) -> PolicyRun:
    """Closed-loop: the policy sees the true state at the start of each step."""
    policy.reset(np.random.default_rng(seed))
    n = len(drive)
    src = co2_source_ppm_per_h(drive.n_children, drive.n_adults, params)
    co2 = np.empty(n + 1)
    pm = np.empty(n + 1)
    co2_mean = np.empty(n)
    pm_mean = np.empty(n)
    idx = np.empty(n, dtype=np.int64)
    co2[0], pm[0] = co2_0, pm_0
    current = initial
    for i in range(n):
        current = policy.act(i, float(co2[i]), float(pm[i]), drive, aa, current)
        idx[i] = current
        a_c, b_c = co2_coeffs(aa.lam[current], drive.co2_out[i], src[i])
        a_p, b_p = pm_coeffs(
            aa.lam[current], aa.pen[current], aa.q_eff_m3_h[current], drive.pm_out[i], params
        )
        c_end, c_avg = relax(co2[i], a_c, b_c, drive.dt_h)
        p_end, p_avg = relax(pm[i], a_p, b_p, drive.dt_h)
        co2[i + 1], co2_mean[i] = float(c_end), float(c_avg)
        pm[i + 1], pm_mean[i] = float(p_end), float(p_avg)
    sim = SimResult(co2=co2, pm=pm, co2_mean=co2_mean, pm_mean=pm_mean)
    return PolicyRun(policy.name, idx, sim, dose.compute_kpis(drive, sim, aa, idx, initial))
