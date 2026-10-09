"""Drives the true rooms forward in 30-second steps, publishes noisy readings, and plays the teacher.

Teacher modes:
- auto: a simulated teacher follows each nudge with probability p_follow after a random delay, and can be
  scripted to say "can't" (e.g. too cold), to open only one side, or to tap "done" without opening.
- ui:   a person taps the buttons; the true room changes when they tap "I've opened them". With
  `partial_first_open`, the first "open both sides" only opens one side, so Khidki has something to catch.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from khidki_core.clock import ist_epoch, ist_minute
from khidki_core.schemas import Purifier, Window
from khidki_services.engine import Engine
from khidki_services.outdoor import OutdoorEvent, ReplayOutdoor
from khidki_sim.room import Sensor, TrueRoom, hidden_truth
from khidki_sim.scenario import Scenario

STEP_S = 30.0

Publish = Callable[[str, dict[str, Any]], None]


def outdoor_for(scenario: Scenario) -> ReplayOutdoor:
    events = []
    for e in scenario.events:
        if e.kind == "outdoor_spike":
            h, m = (int(x) for x in e.at.split(":"))
            start = h * 60 + m
            events.append(OutdoorEvent(start_min=start, end_min=start + e.duration_min, factor=e.factor))
    return ReplayOutdoor(date=scenario.date, events=events)


@dataclass
class _Pending:
    at: float
    fn: Callable[[], None]


@dataclass
class SimDriver:
    engine: Engine
    scenario: Scenario
    outdoor: ReplayOutdoor
    publish: Publish | None = None
    rooms: dict[str, TrueRoom] = field(default_factory=dict)
    t: float = 0.0
    log: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng(self.scenario.seed)
        for r in self.engine.school.rooms:
            if r.room_id in self.scenario.rooms:
                self.rooms[r.room_id] = TrueRoom(r.room_id, hidden_truth(r.params), Sensor.random(self.rng))
        self.t = self.engine.clock.now()
        self._pending: list[_Pending] = []
        self._handled: set[str] = set()
        self._opens_seen = 0
        self._cant_used = False
        self._fake_used = False
        self.engine.on_nudge.append(self._on_nudge)
        self.engine.on_ack.append(self._on_ack)
        if self.publish is None:
            self.publish = self.engine.ingest

    @classmethod
    def start_of_day(cls, engine: Engine, scenario: Scenario, outdoor: ReplayOutdoor) -> SimDriver:
        """Rooms start the day shut, with yesterday's air: a little stale CO₂ and outdoor-ish PM."""
        d = cls(engine, scenario, outdoor)
        pm0 = outdoor.true_pm(ist_epoch(scenario.date, 7 * 60))
        for room in d.rooms.values():
            room.co2, room.pm = 520.0, 0.55 * pm0
        return d

    # ── physics ──────────────────────────────────────────────────────────────────────────────────────
    def advance(self, until: float) -> int:
        n = 0
        while self.t + STEP_S <= until:
            self.t += STEP_S
            for p in sorted([p for p in self._pending if p.at <= self.t], key=lambda p: p.at):
                self._pending.remove(p)
                p.fn()
            self._watch_follow_ups()
            minute = ist_minute(self.t)
            pm_out = self.outdoor.true_pm(self.t)
            for rid, room in self.rooms.items():
                kids, adults = self.engine.occupants_at(rid, minute)
                room.step(STEP_S, pm_out, 450.0, kids, adults)
                co2, pm = room.sensor.read(room.co2, room.pm)
                assert self.publish is not None
                self.publish(rid, {"ts": self.t, "co2": co2, "pm25": pm, "simulated": True})
            n += 1
        return n

    # ── teacher ──────────────────────────────────────────────────────────────────────────────────────
    def _physically_set(self, room_id: str, action: dict[str, str], *, follow_up: bool = False) -> None:
        room = self.rooms[room_id]
        w, a = Window(action["window"]), Purifier(action["purifier"])
        lam_override = None
        opening = list(Window).index(w) > list(Window).index(room.window) or follow_up
        if w == Window.OPEN_BOTH and opening and not follow_up:
            self._opens_seen += 1
            if self.scenario.teacher.partial_first_open and self._opens_seen == 1:
                w = Window.OPEN_ONE  # only the road side: the room gets its one-side air-change rate
                self.log.append(f"{room_id}: only the road side opened")
        room.set(w, a, self.t, lam_override)
        self.log.append(f"{room_id}: windows {w.value}, purifier {a.value}")

    def _on_nudge(self, room_id: str, nudge: dict[str, Any]) -> None:
        if room_id not in self.rooms or self.scenario.teacher.mode != "auto":
            return
        spec = self.scenario.teacher
        lo, hi = spec.delay_s
        delay = float(self.rng.uniform(lo, hi))
        nid = nudge["nudge_id"]
        opening = list(Window).index(Window(nudge["action"]["window"])) > list(Window).index(
            Window(nudge["from"]["window"])
        )
        if spec.cant_first and opening and not self._cant_used:
            self._cant_used = True
            reason = spec.cant_first
            self._later(delay, lambda: self.engine.ack(nid, "cant", reason))
            return
        if spec.fake_confirm_first and opening and not self._fake_used:
            self._fake_used = True
            self._later(delay, lambda: self.engine.ack(nid, "done"))
            return
        if self.rng.random() >= spec.p_follow:
            self.log.append(f"{room_id}: teacher missed {nid}")
            return

        def act() -> None:
            self._physically_set(room_id, nudge["action"])
            self._later(10, lambda: self._safe_ack(nid))

        self._later(delay, act)

    def _safe_ack(self, nid: str) -> None:
        with contextlib.suppress(KeyError):
            self.engine.ack(nid, "done")

    def _on_ack(self, room_id: str, nudge: dict[str, Any]) -> None:
        if room_id not in self.rooms or self.scenario.teacher.mode != "ui" or nudge.get("ack") != "done":
            return
        follow_up = nudge["state"].get("status") == "follow_up" or nudge["state"].get("attempt", 1) > 1
        self._physically_set(room_id, nudge["action"], follow_up=follow_up)

    def _watch_follow_ups(self) -> None:
        """In auto mode, a teacher shown "only one side seems open" opens the other side and taps again."""
        if self.scenario.teacher.mode != "auto":
            return
        for rid in self.rooms:
            st = self.engine.store.get(f"ROOM#{rid}", "STATE")
            if not st or not st["open_nudge"]:
                continue
            n = self.engine.store.get(f"ROOM#{rid}", st["open_nudge"])
            if not n or n["state"]["status"] != "follow_up" or n["nudge_id"] in self._handled:
                continue
            self._handled.add(n["nudge_id"])
            nid, action = n["nudge_id"], n["action"]

            def fix(rid: str = rid, nid: str = nid, action: dict[str, str] = action) -> None:
                self._physically_set(rid, action, follow_up=True)
                self._later(10, lambda: self._safe_ack(nid))

            self._later(float(self.rng.uniform(20, 60)), fix)

    def _later(self, delay_s: float, fn: Callable[[], None]) -> None:
        self._pending.append(_Pending(self.t + delay_s, fn))
