"""Turn an optimizer result into a Plan: per-step actions with reason codes, and human instructions.

Also applies teacher "can't right now" constraints:
- cold: the cold weight β doubles for the rest of the day
- exam: the window state is frozen for the period
- noise: windows can at most be cracked for the period
- rain: no open windows until the constraint ends (the service sets it to 30 minutes)
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from khidki_core.baselines import run_policy, standard_baselines
from khidki_core.optimizer import (
    BoolArray,
    CostConfig,
    MaskFn,
    OptResult,
    allow_all,
    co2_band,
    optimize,
)
from khidki_core.physics import ActionArrays, DriveSeries, action_arrays
from khidki_core.schemas import (
    PROFILE_ALPHA,
    Action,
    Constraint,
    Instruction,
    Kpis,
    Plan,
    PlanStep,
    Profile,
    ReasonCode,
    RoomParams,
    Window,
)
from khidki_core.timetable import hhmm

OPEN_WINDOWS = (Window.OPEN_ONE, Window.OPEN_BOTH)


def apply_constraints(
    allowed: BoolArray, drive: DriveSeries, aa: ActionArrays, constraints: Sequence[Constraint]
) -> BoolArray:
    out = allowed.copy()
    for c in constraints:
        in_window = (drive.t_min >= c.start_min) & (drive.t_min < c.end_min)
        if c.kind in ("noise", "rain"):
            for a, act in enumerate(aa.actions):
                if act.window in OPEN_WINDOWS:
                    out[in_window, :, a] = False
        elif c.kind == "exam":
            for a, act in enumerate(aa.actions):
                if act.window != c.window_at_start:
                    out[in_window, :, a] = False
    return out


def cost_config(profile: Profile, constraints: Sequence[Constraint], beta: float = 0.3) -> CostConfig:
    if any(c.kind == "cold" for c in constraints):
        beta *= 2
    return CostConfig(alpha=PROFILE_ALPHA[profile], beta=beta)


def _reason(
    i: int, idx: np.ndarray, prev: int, res: OptResult, drive: DriveSeries, aa: ActionArrays, pm_low: float
) -> ReasonCode:
    before = int(idx[i - 1]) if i > 0 else prev
    now = int(idx[i])
    if now == before:
        return ReasonCode.KEEP_STEADY
    w_before, w_now = aa.window_idx[before], aa.window_idx[now]
    co2_now = float(res.sim.co2[i])
    kids = bool(drive.children_present[i])
    if w_now > w_before:
        if not kids:
            return ReasonCode.RECESS_PURGE
        if co2_now >= 1200 or res.sim.co2[i + 1] > co2_now + 50:
            return ReasonCode.CO2_RISING_FAST
        if drive.pm_out[i] <= pm_low:
            return ReasonCode.OUTDOOR_PM_LOW_WINDOW
        return ReasonCode.CO2_RISING_FAST
    if w_now == w_before:  # purifier change only
        return ReasonCode.PURIFIER_DURING_CLOSED
    if aa.actions[now].window in OPEN_WINDOWS:  # less open, still open: CO₂ is flushed, let less smog in
        return ReasonCode.AIR_REFRESHED
    ahead = drive.pm_out[i : i + 6]
    if len(ahead) > 1 and float(np.mean(ahead[1:])) > 1.15 * float(drive.pm_out[i]):
        return ReasonCode.OUTDOOR_PM_SPIKE_CLOSE
    band = int(co2_band(co2_now))
    open_actions = [a for a, act in enumerate(aa.actions) if act.window == Window.OPEN_BOTH]
    if open_actions and not res.allowed[i, band, open_actions[0]]:
        return ReasonCode.POLICY_FORBIDS_OPEN
    if aa.purifier_on[now]:
        return ReasonCode.PURIFIER_DURING_CLOSED
    if co2_now < 1100 or drive.temp_out[i] >= 18:
        return ReasonCode.AIR_REFRESHED
    return ReasonCode.COLD_LIMIT


def build_plan(
    room_id: str,
    date: str,
    params: RoomParams,
    drive: DriveSeries,
    co2_0: float,
    pm_0: float,
    prev_action: Action,
    profile: Profile = Profile.BALANCED,
    max_changes: int = 6,
    constraints: Sequence[Constraint] = (),
    mask_fn: MaskFn | None = None,
    version: int = 1,
    with_baselines: bool = True,
) -> tuple[Plan, OptResult]:
    aa = action_arrays(params)
    if prev_action not in aa.actions:
        prev_action = Action(window=prev_action.window)
    prev = aa.index(prev_action)
    allowed = (mask_fn or allow_all)(drive, aa)
    allowed = apply_constraints(allowed, drive, aa, constraints)
    cfg = cost_config(profile, constraints)
    res = optimize(params, drive, aa, co2_0, pm_0, prev, cfg, max_changes, allowed)

    occ_pm = drive.pm_out[drive.children_present]
    pm_low = float(np.percentile(occ_pm, 33)) if len(occ_pm) else float(np.min(drive.pm_out))
    idx = res.action_idx
    steps: list[PlanStep] = []
    for i in range(len(drive)):
        act = aa.actions[int(idx[i])]
        steps.append(
            PlanStep(
                t_min=int(drive.t_min[i]),
                t=hhmm(int(drive.t_min[i])),
                window=act.window,
                purifier=act.purifier,
                predicted_co2=round(float(res.sim.co2_mean[i])),
                predicted_pm=round(float(res.sim.pm_mean[i]), 1),
                occupied=bool(drive.children_present[i]),
                reason_code=_reason(i, idx, prev, res, drive, aa, pm_low),
            )
        )

    change_at = [i for i in range(len(drive)) if int(idx[i]) != (int(idx[i - 1]) if i > 0 else prev)]
    end_of_horizon = int(drive.t_min[-1]) + drive.dt_min
    instructions: list[Instruction] = []
    for n, i in enumerate(change_at):
        t_end = int(drive.t_min[change_at[n + 1]]) if n + 1 < len(change_at) else end_of_horizon
        instructions.append(
            Instruction(
                t_start_min=int(drive.t_min[i]),
                t_end_min=t_end,
                t_start=hhmm(int(drive.t_min[i])),
                action=aa.actions[int(idx[i])],
                duration_min=t_end - int(drive.t_min[i]),
                reason_code=steps[i].reason_code,
            )
        )

    baselines: dict[str, Kpis] = {}
    if with_baselines:
        for pol in standard_baselines():
            baselines[pol.name] = run_policy(params, drive, aa, pol, co2_0, pm_0, prev).kpis

    plan = Plan(
        room_id=room_id,
        date=date,
        version=version,
        profile=profile,
        mu=res.mu,
        budget_binding=res.budget_binding,
        steps=steps,
        instructions=instructions,
        kpis_predicted=res.kpis,
        baselines_predicted=baselines,
        constraints=list(constraints),
    )
    return plan, res
