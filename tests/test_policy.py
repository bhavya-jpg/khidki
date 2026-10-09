"""Cedar policies: schema validation, a positive and negative case per policy, and access control."""

import numpy as np
import pytest

from khidki_core.physics import action_arrays
from khidki_core.policy import POLICIES, CedarPolicy, validate
from khidki_core.schemas import RoomParams, Window
from khidki_core.synthetic import severe_morning

CEDAR = CedarPolicy(
    rooms={"6B": {"grade": 6}, "3A": {"grade": 3, "has_purifier": True}},
    users={
        "teacher-6B": {"role": "teacher", "room": "6B"},
        "parent-6B": {"role": "parent", "room": "6B"},
        "principal": {"role": "principal"},
    },
)


def test_policies_validate_against_schema() -> None:
    ok, errors = validate()
    assert ok, errors


def test_every_policy_is_explained_in_both_languages() -> None:
    for pid, info in POLICIES.items():
        assert info.en and info.hi, pid


@pytest.mark.parametrize(
    ("pm", "band", "allowed", "ids"),
    [
        (300, 2, False, ("S1",)),  # severe outside, CO₂ fine: stay shut
        (300, 4, True, ("P-vent",)),  # severe outside but CO₂ ≥ 2,000: opening allowed
        (200, 2, True, ("P-vent",)),
    ],
)
def test_s1_open_in_severe_air(pm: int, band: int, allowed: bool, ids: tuple[str, ...]) -> None:
    d = CEDAR.ventilation(Window.OPEN_BOTH, pm, band, grap_stage=2, room_id="6B")
    assert (d.allowed, d.policy_ids) == (allowed, ids)


def test_closing_is_always_allowed() -> None:
    assert CEDAR.ventilation(Window.CLOSED, 400, 0, grap_stage=4, room_id="6B").allowed


@pytest.mark.parametrize(
    ("pm", "stage", "grade", "allowed", "fired"),
    [
        (142, 1, 6, False, {"S2"}),
        (80, 1, 6, True, set()),
        (70, 1, 3, False, {"S3"}),
        (50, 3, 6, False, {"S4"}),
        (95, 3, 3, False, {"S2", "S3", "S4"}),
    ],
)
def test_activity_policies(pm: int, stage: int, grade: int, allowed: bool, fired: set[str]) -> None:
    d = CEDAR.activity_decision("pe", pm, stage, grade)
    assert d.allowed == allowed
    if not allowed:
        assert set(d.policy_ids) == fired


def test_teacher_sees_own_room_but_cannot_override() -> None:
    assert CEDAR.authorize("teacher-6B", "view.room", "Room", "6B").allowed
    assert not CEDAR.authorize("teacher-6B", "view.room", "Room", "3A").allowed
    d = CEDAR.authorize("teacher-6B", "plan.override", "School", "dsv")
    assert not d.allowed and d.policy_ids == ("A3",)
    assert not CEDAR.authorize("parent-6B", "grap.setOfficial", "School", "dsv").allowed


def test_principal_can_override_and_see_everything() -> None:
    assert CEDAR.authorize("principal", "plan.override", "School", "dsv").allowed
    assert CEDAR.authorize("principal", "view.room", "Room", "3A").allowed
    assert CEDAR.authorize("principal", "view.school", "School", "dsv").allowed


def test_mask_blocks_opening_in_severe_air_only_below_2000_ppm() -> None:
    room = RoomParams()
    drive = severe_morning(room)
    drive = type(drive)(**{**drive.__dict__, "pm_out": np.full(len(drive), 300.0)})
    aa = action_arrays(room)
    mask = CEDAR.ventilation_mask(drive, aa, grap_stage=3)
    open_both = aa.actions.index(next(a for a in aa.actions if a.window == Window.OPEN_BOTH))
    closed = aa.actions.index(next(a for a in aa.actions if a.window == Window.CLOSED))
    assert not mask[:, :4, open_both].any()
    assert mask[:, 4, open_both].all()
    assert mask[:, :, closed].all()


def test_engine_moves_pe_indoors_with_policy_id() -> None:
    from khidki_core.clock import SimClock
    from khidki_services.engine import Engine
    from khidki_services.outdoor import ReplayOutdoor
    from khidki_services.store import MemoryStore

    t = [1_000_000.0]
    clock = SimClock(real_time=lambda: t[0])
    clock.start_demo("2025-11-18", "07:00", 1.0)
    engine = Engine(MemoryStore(), clock, ReplayOutdoor("2025-11-18"))
    engine.seed()
    view = engine.school_today()
    pe = next(d for d in view["decisions"] if d["key"] == "pe:6B")
    assert pe["outdoor"] is False and "S2" in pe["policy_ids"]
    assert "S2" in view["policies"] and view["policies"]["S2"]["hi"]


def test_override_is_principal_only_logged_and_replans() -> None:
    from khidki_core.clock import SimClock
    from khidki_core.optimizer import Grid
    from khidki_services.engine import Engine
    from khidki_services.outdoor import ReplayOutdoor
    from khidki_services.store import MemoryStore

    t = [1_000_000.0]
    clock = SimClock(real_time=lambda: t[0])
    clock.start_demo("2025-11-18", "07:00", 1.0)
    engine = Engine(MemoryStore(), clock, ReplayOutdoor("2025-11-18"), grid=Grid(co2_step=50, pm_step=5))
    engine.seed()
    with pytest.raises(PermissionError):
        engine.override("pe:6B", True, "sports day", user_id="teacher-6B")
    with pytest.raises(ValueError):
        engine.override("pe:6B", True, "  ", user_id="principal")
    entry = engine.override("pe:6B", True, "Inter-school match, masks given", user_id="principal")
    assert entry["by"] == "principal" and entry["was_outdoor"] is False and "S2" in entry["policy_ids"]
    pe = next(d for d in engine.school_today()["decisions"] if d["key"] == "pe:6B")
    assert pe["override"] is True and pe["override_reason"].startswith("Inter-school")
    assert engine.audit()[0]["key"] == "pe:6B"
    assert engine.occupancy_flags("6B")["pe_outdoor"] is True
