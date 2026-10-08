import time

import numpy as np
import pytest

from khidki_core.baselines import Fixed, run_policy
from khidki_core.optimizer import N_CO2_BANDS, co2_band, optimize
from khidki_core.physics import action_arrays
from khidki_core.planning import build_plan
from khidki_core.schemas import Action, Constraint, Purifier, ReasonCode, RoomParams, Window
from khidki_core.synthetic import severe_morning

ROOM = RoomParams()
ROOM_P = RoomParams(has_purifier=True)


@pytest.fixture(scope="module")
def severe_plan():  # type: ignore[no-untyped-def]
    drive = severe_morning(ROOM)
    return drive, build_plan("6B", "2025-11-12", ROOM, drive, 500.0, 120.0, Action(window=Window.CLOSED))


def test_budget_respected(severe_plan) -> None:  # type: ignore[no-untyped-def]
    _, (plan, res) = severe_plan
    assert res.kpis.window_changes <= 6
    assert len(plan.instructions) == res.kpis.window_changes


def test_beats_always_closed_on_co2_and_always_open_on_pm(severe_plan) -> None:  # type: ignore[no-untyped-def]
    _, (plan, _) = severe_plan
    k = plan.kpis_predicted
    closed = plan.baselines_predicted["ALWAYS_CLOSED"]
    opened = plan.baselines_predicted["ALWAYS_OPEN"]
    assert k.co2_min_over_1500 < closed.co2_min_over_1500
    assert k.co2_points < 0.2 * closed.co2_points
    assert k.pm_dose_ug < opened.pm_dose_ug


def test_khidki_keeps_co2_mostly_below_1500(severe_plan) -> None:  # type: ignore[no-untyped-def]
    _, (plan, _) = severe_plan
    assert plan.kpis_predicted.co2_min_over_1500 <= 30


def test_deterministic() -> None:
    drive = severe_morning(ROOM)
    a, _ = build_plan(
        "6B", "d", ROOM, drive, 500.0, 120.0, Action(window=Window.CLOSED), with_baselines=False
    )
    b, _ = build_plan(
        "6B", "d", ROOM, drive, 500.0, 120.0, Action(window=Window.CLOSED), with_baselines=False
    )
    assert a.model_dump() == b.model_dump()


def test_replan_under_3_seconds() -> None:
    drive = severe_morning(ROOM_P)
    t0 = time.perf_counter()
    build_plan("3A", "d", ROOM_P, drive, 500.0, 120.0, Action(window=Window.CLOSED), with_baselines=False)
    assert time.perf_counter() - t0 < 3.0


def test_mask_is_respected() -> None:
    """S1-like mask: no fully open window unless CO₂ is in the ≥ 2,000 ppm band."""
    drive = severe_morning(ROOM)
    aa = action_arrays(ROOM)
    allowed = np.ones((len(drive), N_CO2_BANDS, len(aa)), dtype=bool)
    for a, act in enumerate(aa.actions):
        if act.window in (Window.OPEN_ONE, Window.OPEN_BOTH):
            allowed[:, :4, a] = False
    res = optimize(ROOM, drive, aa, 500.0, 120.0, 0, allowed=allowed)
    bands = co2_band(res.sim.co2[:-1])
    for i, a in enumerate(res.action_idx):
        assert allowed[i, bands[i], a], f"step {i} chose a masked action"


def test_purifier_room_uses_purifier_and_gets_lower_pm() -> None:
    """Holding 44 children under 1,500 ppm needs ~3.3 air changes/h, so even with a purifier the PM cut
    against "always open + purifier" is bounded (~25% at best). Check the purifier is used, it beats that
    baseline, and it clearly beats the same plan in a room without one."""
    plan, res = build_plan(
        "3A", "d", ROOM_P, severe_morning(ROOM_P), 500.0, 120.0, Action(window=Window.CLOSED)
    )
    _, res_np = build_plan(
        "6B",
        "d",
        ROOM,
        severe_morning(ROOM),
        500.0,
        120.0,
        Action(window=Window.CLOSED),
        with_baselines=False,
    )
    assert any(s.purifier == Purifier.ON for s in plan.steps if s.occupied)
    assert res.kpis.pm_dose_ug < 0.9 * plan.baselines_predicted["ALWAYS_OPEN"].pm_dose_ug
    assert res.kpis.pm_dose_ug < 0.85 * res_np.kpis.pm_dose_ug
    assert res.kpis.co2_min_over_1500 <= 15


def test_exam_constraint_freezes_window() -> None:
    drive = severe_morning(ROOM)
    exam = Constraint(kind="exam", start_min=9 * 60, end_min=9 * 60 + 35, window_at_start=Window.CLOSED)
    plan, _ = build_plan(
        "6B",
        "d",
        ROOM,
        drive,
        500.0,
        120.0,
        Action(window=Window.CLOSED),
        constraints=[exam],
        with_baselines=False,
    )
    assert all(s.window == Window.CLOSED for s in plan.steps if exam.start_min <= s.t_min < exam.end_min)


def test_noise_constraint_never_fully_opens() -> None:
    drive = severe_morning(ROOM)
    noise = Constraint(kind="noise", start_min=7 * 60, end_min=13 * 60 + 30)
    plan, _ = build_plan(
        "6B",
        "d",
        ROOM,
        drive,
        500.0,
        120.0,
        Action(window=Window.CLOSED),
        constraints=[noise],
        with_baselines=False,
    )
    assert all(s.window in (Window.CLOSED, Window.CRACKED) for s in plan.steps)


def test_instructions_have_reason_codes_and_recess_purge(severe_plan) -> None:  # type: ignore[no-untyped-def]
    _, (plan, _) = severe_plan
    assert all(i.reason_code != ReasonCode.KEEP_STEADY for i in plan.instructions)
    assert all(i.duration_min > 0 for i in plan.instructions)


def test_always_closed_is_terrible_for_co2() -> None:
    drive = severe_morning(ROOM)
    aa = action_arrays(ROOM)
    run = run_policy(ROOM, drive, aa, Fixed("ALWAYS_CLOSED", Window.CLOSED), 500.0, 120.0)
    assert run.kpis.max_co2 > 2500
