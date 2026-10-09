"""The web app's TypeScript types must match what the engine returns (web/src/types.ts)."""

import re
from pathlib import Path

from khidki_core.clock import SimClock
from khidki_core.optimizer import Grid
from khidki_services.engine import Engine
from khidki_services.outdoor import ReplayOutdoor
from khidki_services.store import MemoryStore

TYPES = (Path(__file__).parents[1] / "web" / "src" / "types.ts").read_text()


def ts_keys(interface: str) -> set[str]:
    body = re.search(rf"export interface {interface} \{{(.*?)\n\}}", TYPES, re.S)
    assert body, interface
    return set(re.findall(r"^  (\w+)\??:", body.group(1), re.M))


def test_room_now_matches_types() -> None:
    t = [1_000_000.0]
    clock = SimClock(real_time=lambda: t[0])
    clock.start_demo("2025-11-18", "08:00", 1.0)
    engine = Engine(MemoryStore(), clock, ReplayOutdoor("2025-11-18"), grid=Grid(co2_step=50, pm_step=5))
    engine.seed()
    engine.tick()
    view = engine.room_now("6B")
    assert set(view) == ts_keys("RoomNow")
    assert set(view["clock"]) == ts_keys("ClockView")
    card_type = "KeepCard" if view["card"]["kind"] == "keep" else "ActionCard"
    assert set(view["card"]) == ts_keys(card_type)
