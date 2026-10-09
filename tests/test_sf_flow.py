"""The cloud path: Step Functions drives the nudge (task tokens, waits, verify) through the engine's
sf_* entry points, on the same simulated room as local mode."""

from khidki_core.clock import SimClock
from khidki_core.optimizer import Grid
from khidki_services.engine import Engine
from khidki_services.store import MemoryStore
from khidki_sim import scenario as scenarios
from khidki_sim.driver import SimDriver, outdoor_for


def setup(name: str):  # type: ignore[no-untyped-def]
    sc = scenarios.load(name)
    t = [1_000_000.0]
    clock = SimClock(real_time=lambda: t[0])
    clock.start_demo(sc.date, sc.start, 1.0)
    outdoor = outdoor_for(sc)
    engine = Engine(
        MemoryStore(),
        clock,
        outdoor,
        grid=Grid(co2_step=50, pm_step=5),
        replan_every_s=600,
        external_nudges=True,
    )
    engine.seed()
    sent: list[tuple[str, dict]] = []  # type: ignore[type-arg]
    engine.task_notifier = lambda token, out: sent.append((token, out))
    sim = SimDriver.start_of_day(engine, sc, outdoor)

    def advance(seconds: float) -> None:
        end = t[0] + seconds
        while t[0] < end:
            t[0] += 30
            sim.advance(clock.now())
            engine.tick()

    return engine, sim, advance, sent


def open_nudge(engine: Engine, room: str = "6B") -> str | None:
    st = engine.store.get(f"ROOM#{room}", "STATE")
    if not st or not st["open_nudge"]:
        return None
    n = engine.store.get(f"ROOM#{room}", st["open_nudge"])
    return n["nudge_id"] if n else None


def test_step_functions_path_catches_partial_open_then_verifies() -> None:
    engine, sim, advance, sent = setup("partial_open")

    def finish(nid: str) -> None:
        """Play Step Functions for an instruction we're not testing: tap, wait, verify (follow up once)."""
        for _ in range(2):
            engine.sf_await_ack(nid, f"t-{nid}")
            engine.ack(nid, "done")
            advance(180)
            if engine.sf_verify(nid)["status"] == "done":
                return

    nid = None
    for _ in range(600):
        advance(30)
        nid = open_nudge(engine)
        if not nid:
            continue
        if engine.store.get("ROOM#6B", engine.find_nudge(nid)[1])["action"]["window"] == "open_both":
            break
        finish(nid)
        nid = None
    assert nid, "no open-both instruction was issued"
    secs = engine.sf_await_ack(nid, "token-1")
    assert secs["status"] == "issued" and secs["verify_wait_s"] == 180

    engine.ack(nid, "done")  # the teacher taps; the sim opens only the road side
    assert sent[-1][0] == "token-1" and sent[-1][1]["result"] == "done"
    advance(180)
    v = engine.sf_verify(nid)
    assert v["status"] == "follow_up" and v["follow_up"] == "other_side", v

    engine.sf_await_ack(nid, "token-2")
    engine.ack(nid, "done")  # the corridor side opens too
    assert sent[-1][0] == "token-2"
    advance(180)
    v = engine.sf_verify(nid)
    assert v["status"] == "done" and v["outcome"] == "verified", v
    assert any("only the road side" in line for line in sim.log)


def test_tap_before_token_is_handed_straight_back_and_timeout_goes_to_verify() -> None:
    engine, _, advance, sent = setup("partial_open")
    nid = None
    for _ in range(400):
        advance(30)
        nid = open_nudge(engine)
        if nid:
            break
    assert nid
    # Nobody taps: Step Functions times out and the nudge moves to verification without a tap.
    engine.sf_await_ack(nid, "token-a")
    v = engine.sf_timeout(nid)
    assert v["status"] == "verifying" and v["ack"] == "no_ack"
    # A token parked after the nudge has moved on is released at once.
    engine.sf_await_ack(nid, "token-b")
    assert sent and sent[-1][0] == "token-b"
