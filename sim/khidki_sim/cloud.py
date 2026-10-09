"""Drive the deployed Khidki from this laptop: the true classrooms live here, readings go to POST /v1/ingest
(API Gateway → Lambda), and the teacher is played by watching the API.

Teacher modes (from the scenario):
- auto: follows each instruction after a delay (taps "I've opened them" through the API)
- ui:   a person taps in the web app; when the instruction changes to "checking", the true room changes.
        With partial_first_open, the first "open both sides" only opens the road side.

Usage: python tasks.py sim --scenario partial_open --speed 10 --target cloud
"""

from __future__ import annotations

import contextlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from khidki_core.clock import ist_minute
from khidki_core.schemas import Purifier, Window
from khidki_core.timetable import default_timetable, occupancy
from khidki_services.seed import DEMO_SCHOOL
from khidki_sim.driver import STEP_S, outdoor_for
from khidki_sim.room import Sensor, TrueRoom, hidden_truth
from khidki_sim.scenario import Scenario


def _req(
    method: str, url: str, body: Any = None, headers: dict[str, str] | None = None, timeout: float = 20
) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"content-type": "application/json", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "null")


@dataclass
class CloudSim:
    api: str
    device_key: str
    admin_key: str
    scenario: Scenario
    speed: float
    rooms: dict[str, TrueRoom] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.api = self.api.rstrip("/")
        self.rng = np.random.default_rng(self.scenario.seed)
        self.outdoor = outdoor_for(self.scenario)
        for r in DEMO_SCHOOL.rooms:
            if r.room_id in self.scenario.rooms:
                self.rooms[r.room_id] = TrueRoom(r.room_id, hidden_truth(r.params), Sensor.random(self.rng))
        self.t = 0.0
        self._flags: dict[str, dict[str, Any]] = {}
        self._flags_at = 0.0
        self._seen: dict[str, str] = {}
        self._pending: list[tuple[float, Any]] = []
        self._opens = 0

    # ── control ─────────────────────────────────────────────────────────────────────────────────────
    def start(self) -> None:
        r = _req(
            "POST",
            f"{self.api}/v1/sim/control",
            {"action": "scenario", "scenario": self.scenario.name, "speed": self.speed},
            {"x-khidki-admin": self.admin_key},
        )
        self.t = float(r["clock"]["now"])
        pm0 = self.outdoor.true_pm(self.t)
        for room in self.rooms.values():
            room.co2, room.pm = 520.0, 0.55 * pm0
        print(f"Started '{self.scenario.name}' at {r['clock']['time']} ({self.speed:g}× speed) on {self.api}")

    def sim_now(self) -> float:
        return float(_req("GET", f"{self.api}/v1/health")["clock"]["now"])

    # ── occupancy follows the school's decisions (assembly, recess, PE) ────────────────────────────
    def flags(self, room_id: str) -> dict[str, Any]:
        if time.time() - self._flags_at > 60 or room_id not in self._flags:
            today = _req("GET", f"{self.api}/v1/schools/{DEMO_SCHOOL.school_id}/today")
            dec = {
                d["key"]: (d["override"] if d["override"] is not None else d["outdoor"])
                for d in today["decisions"]
            }
            for r in DEMO_SCHOOL.rooms:
                self._flags[r.room_id] = {
                    "assembly_outdoor": dec.get("assembly", True),
                    "recess_outdoor": dec.get("recess_outdoor", True),
                    "pe_period": r.pe_period,
                    "pe_outdoor": dec.get(f"pe:{r.room_id}", False),
                }
            self._flags_at = time.time()
        return self._flags[room_id]

    def occupants(self, room_id: str, minute: float) -> tuple[float, float]:
        room = self.rooms[room_id]
        kids, adults = occupancy(
            np.array([int(minute)], dtype=np.int64),
            room.params.students,
            room.params.adults,
            timetable=default_timetable(),
            **self.flags(room_id),
        )
        return float(kids[0]), float(adults[0])

    # ── the loop ────────────────────────────────────────────────────────────────────────────────────
    def step_until(self, now: float) -> None:
        batch: list[dict[str, Any]] = []
        while self.t + STEP_S <= now:
            self.t += STEP_S
            for due, fn in [p for p in self._pending if p[0] <= self.t]:
                self._pending.remove((due, fn))
                fn()
            minute = ist_minute(self.t)
            pm_out = self.outdoor.true_pm(self.t)
            for rid, room in self.rooms.items():
                kids, adults = self.occupants(rid, minute)
                room.step(STEP_S, pm_out, 450.0, kids, adults)
                co2, pm = room.sensor.read(room.co2, room.pm)
                batch.append({"room_id": rid, "ts": self.t, "co2": co2, "pm25": pm, "simulated": True})
        for i in range(0, len(batch), 40):
            _req(
                "POST",
                f"{self.api}/v1/ingest",
                {"readings": batch[i : i + 40]},
                {"x-khidki-device-key": self.device_key},
            )

    def set_window(self, room_id: str, action: dict[str, str], follow_up: bool = False) -> None:
        room = self.rooms[room_id]
        w, a = Window(action["window"]), Purifier(action["purifier"])
        if w == Window.OPEN_BOTH and not follow_up:
            self._opens += 1
            if self.scenario.teacher.partial_first_open and self._opens == 1:
                w = Window.OPEN_ONE
                self.log.append(f"{room_id}: only the road side opened")
        room.set(w, a, self.t)
        self.log.append(f"{room_id}: windows {w.value}, purifier {a.value}")
        print(f"  [{room_id}] windows {w.value}, purifier {a.value}")

    def watch_teacher(self) -> None:
        for rid in self.rooms:
            card = _req("GET", f"{self.api}/v1/rooms/{rid}/now")["card"]
            if card["kind"] != "action":
                continue
            key = f"{card['nudge_id']}:{card['status']}"
            if self._seen.get(rid) == key:
                continue
            prev = self._seen.get(rid, "")
            self._seen[rid] = key
            mode = self.scenario.teacher.mode
            if mode == "ui" and card["status"] == "verifying" and not prev.endswith(":verifying"):
                self.set_window(rid, card["action"], follow_up=":follow_up" in prev)
            elif mode == "auto" and card["status"] in ("issued", "follow_up"):
                if card["status"] == "issued" and self.rng.random() >= self.scenario.teacher.p_follow:
                    print(f"  [{rid}] the simulated teacher misses this one")
                    continue
                lo, hi = self.scenario.teacher.delay_s
                delay = float(self.rng.uniform(lo, hi))
                nid, action, fu = card["nudge_id"], card["action"], card["status"] == "follow_up"

                def act(
                    rid: str = rid, nid: str = nid, action: dict[str, str] = action, fu: bool = fu
                ) -> None:
                    self.set_window(rid, action, follow_up=fu)
                    with contextlib.suppress(urllib.error.HTTPError):
                        _req("POST", f"{self.api}/v1/nudges/{nid}/ack", {"result": "done"})

                self._pending.append((self.t + delay, act))

    def run(self, minutes: float | None = None) -> None:
        self.start()
        started = time.time()
        while minutes is None or time.time() - started < minutes * 60:
            try:
                self.step_until(self.sim_now())
                self.watch_teacher()
            except urllib.error.URLError as exc:
                print(f"  network hiccup: {exc}; retrying")
            time.sleep(1.5)
