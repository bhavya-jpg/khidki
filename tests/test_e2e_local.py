"""Local mode end to end: replay day + simulated room + engine, on a fake fast clock."""

from collections.abc import Callable

from khidki_core.clock import SimClock
from khidki_core.optimizer import Grid
from khidki_services.engine import Engine
from khidki_services.store import MemoryStore
from khidki_sim import scenario as scenarios
from khidki_sim.driver import SimDriver, outdoor_for

COARSE = Grid(co2_step=50.0, pm_step=5.0)


def run(name: str, until: str, on_step: Callable[[Engine], None] | None = None) -> tuple[Engine, SimDriver]:
    sc = scenarios.load(name)
    t = [1_000_000.0]
    clock = SimClock(real_time=lambda: t[0])
    clock.start_demo(sc.date, sc.start, 1.0)
    outdoor = outdoor_for(sc)
    engine = Engine(MemoryStore(), clock, outdoor, grid=COARSE, replan_every_s=600)
    engine.seed()
    sim = SimDriver.start_of_day(engine, sc, outdoor)
    h, m = (int(x) for x in until.split(":"))
    while clock.minute_of_day() < h * 60 + m:
        t[0] += 30
        sim.advance(clock.now())
        engine.tick()
        if on_step:
            on_step(engine)
    return engine, sim


def nudges(engine: Engine, room: str) -> list[dict]:  # type: ignore[type-arg]
    return engine.store.query(f"ROOM#{room}", "NUDGE#")


def test_severe_morning_verifies_and_respects_budget() -> None:
    engine, _ = run("severe_morning", "11:00")
    outcomes = [n["state"]["outcome"] for r in ("6B", "3A") for n in nudges(engine, r)]
    assert "verified" in outcomes
    for r in ("6B", "3A"):
        assert len(nudges(engine, r)) <= engine.school.max_changes
    view = engine.room_now("6B")
    assert view["requests"] == {"used": len(nudges(engine, "6B")), "max": engine.school.max_changes}
    assert view["simulated"] and view["clock"]["simulated"]
    assert view["card"]["kind"] in ("keep", "action")


def test_partial_open_is_caught_from_co2() -> None:
    """UI mode: the person taps "I've opened them"; only one side really opens. Khidki should ask for the
    corridor side, and verify after the second tap."""
    tapped: set[tuple[str, int]] = set()

    def teacher_taps(engine: Engine) -> None:
        st = engine.store.get("ROOM#6B", "STATE")
        if not st or not st["open_nudge"]:
            return
        n = engine.store.get("ROOM#6B", st["open_nudge"])
        assert n is not None
        s = n["state"]
        key = (n["nudge_id"], s["attempt"])
        if s["status"] in ("issued", "follow_up") and key not in tapped:
            tapped.add(key)
            engine.ack(n["nudge_id"], "done")

    engine, sim = run("partial_open", "10:10", teacher_taps)
    first_open = next(n for n in nudges(engine, "6B") if n["action"]["window"] == "open_both")
    assert "verdict:partial" in first_open["state"]["history"], first_open["state"]
    assert first_open["state"]["outcome"] == "verified"
    assert any("only the road side" in line for line in sim.log)


def test_teacher_cant_cold_records_constraint_and_replans() -> None:
    engine, _ = run("teacher_cant_cold", "10:00")
    cons = engine.store.query("ROOM#6B", "CONSTRAINT#") + engine.store.query("ROOM#3A", "CONSTRAINT#")
    assert any(c["constraint"]["kind"] == "cold" for c in cons)
    outcomes = [n["state"]["outcome"] for r in ("6B", "3A") for n in nudges(engine, r)]
    assert "not_possible" in outcomes


def test_an_instruction_never_gives_keep_steady_as_its_reason() -> None:
    """ "All fine, keep things as they are" must not appear under "Open the windows", on the teacher card
    or the printable timetable. Found in the audit: a re-plan relabelled the step asking for the change."""
    engine, _ = run("partial_open", "09:00")
    asked = [n for r in ("6B", "3A") for n in nudges(engine, r)]
    assert asked
    assert all(n["reason_code"] != "KEEP_STEADY" for n in asked), [n["reason_code"] for n in asked]
    for room in ("6B", "3A"):
        view = engine.plan_view(room)
        assert view is not None
        keep_en = "All fine. Keep things as they are."
        assert all(row["reason"]["en"] != keep_en for row in view["timetable"]), view["timetable"]


def test_readings_expire_by_the_real_clock_not_the_simulated_one() -> None:
    """A replayed day is months in the past. If a reading's expiry were based on its own timestamp, DynamoDB
    would delete it at once and verification would have nothing to fit (found on the deployed stack)."""
    import time

    engine, _ = run("severe_morning", "07:40")
    rows = engine.telemetry("6B", 0)
    assert rows and all(r["ts"] < time.time() - 86400 for r in rows)  # the replay really is in the past
    assert all(r["ttl"] > time.time() + 3600 for r in rows)
