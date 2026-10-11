"""The live demo's autopilot: the simulated classroom moves only while someone is watching it.

The web page calls `POST /v1/sim/pulse` every few seconds. A pulse moves the true (simulated) rooms forward
to the demo clock, stores their sensor readings and lets the engine tick, which is what the laptop simulator
does through `/v1/ingest`. No visitor means no pulses, so nothing runs and nothing is spent.

The visitor plays the teacher. When an instruction is tapped, or its tap window passes, the true window
changes, and the first "open both sides" only opens the road side so Khidki has something to catch.

A visitor arriving after a pause gets a fresh school morning, already 12 simulated minutes in, so the first
instruction is seconds away. A monthly cap on Step Functions executions keeps the demo inside the AWS free
tier however often it is opened.
"""

from __future__ import annotations

import time
import zlib
from typing import Any

import numpy as np
from botocore.exceptions import ClientError

from khidki_cloud import runtime
from khidki_core.clock import ist_minute
from khidki_core.schemas import Purifier, Window
from khidki_services.dynamo import to_dynamo
from khidki_services.store import Item
from khidki_sim.room import Sensor, TrueRoom, hidden_truth

SCENARIO = "partial_open"
SPEED = 10.0
STEP_S = 30.0  # simulated seconds between sensor readings
WARMUP_MIN = 12  # simulated minutes run at once after a restart
MIN_GAP_S = 1.2  # real seconds between pulses that do work
IDLE_RESTART_S = 45.0  # real seconds without a pulse after which the morning starts again
EXTERNAL_HOLD_S = 90.0  # real seconds to stand back after the laptop simulator posts readings
DAY_END_MIN = 13 * 60 + 35
MAX_STEPS = 16
MONTHLY_EXECUTION_CAP = 300  # about 3,000 of the 4,000 state transitions that are free each month
KEY = ("SIM", "AUTOPILOT")


def budget_key(now: float | None = None) -> tuple[str, str]:
    return "SIM", "BUDGET#" + time.strftime("%Y-%m", time.gmtime(now or time.time()))


def count_execution() -> None:
    """Called whenever a Step Functions execution is started."""
    pk, sk = budget_key()
    runtime.store().table.update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression="ADD executions :one",
        ExpressionAttributeValues={":one": 1},
    )


def mark_external() -> None:
    """The laptop simulator is driving: the autopilot stands back for a while."""
    runtime.store().table.update_item(
        Key={"pk": KEY[0], "sk": KEY[1]},
        UpdateExpression="SET external_at = :now",
        ExpressionAttributeValues=to_dynamo({":now": time.time()}),
    )


def _claim(previous: float | None, now: float) -> bool:
    """Only one pulse at a time does the work, however many pages are open."""
    table = runtime.store().table
    try:
        if previous is None:
            table.update_item(
                Key={"pk": KEY[0], "sk": KEY[1]},
                UpdateExpression="SET last_real = :now",
                ConditionExpression="attribute_not_exists(last_real)",
                ExpressionAttributeValues=to_dynamo({":now": now}),
            )
        else:
            table.update_item(
                Key={"pk": KEY[0], "sk": KEY[1]},
                UpdateExpression="SET last_real = :now",
                ConditionExpression="last_real = :prev",
                ExpressionAttributeValues=to_dynamo({":now": now, ":prev": previous}),
            )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise
    return True


def _rooms(engine: Any, saved: dict[str, Item]) -> dict[str, TrueRoom]:
    rooms: dict[str, TrueRoom] = {}
    for cfg in engine.school.rooms:
        calibration = np.random.default_rng([7, zlib.crc32(cfg.room_id.encode())])
        room = TrueRoom(cfg.room_id, hidden_truth(cfg.params), Sensor.random(calibration))
        s = saved.get(cfg.room_id)
        if s:
            room.co2, room.pm = float(s["co2"]), float(s["pm"])
            room.window, room.purifier = Window(s["window"]), Purifier(s["purifier"])
        rooms[cfg.room_id] = room
    return rooms


def _save(ap: Item, rooms: dict[str, TrueRoom]) -> None:
    ap["rooms"] = {
        rid: {"co2": r.co2, "pm": r.pm, "window": r.window.value, "purifier": r.purifier.value}
        for rid, r in rooms.items()
    }
    runtime.store().put(KEY[0], KEY[1], ap)


def _advance(engine: Any, ap: Item, rooms: dict[str, TrueRoom], until: float, max_steps: int) -> int:
    """Step the true rooms to `until` and hand their readings to the engine, as a sensor would."""
    steps = 0
    last: dict[str, Item] = {}
    while float(ap["t"]) + STEP_S <= until and steps < max_steps:
        ap["t"] = float(ap["t"]) + STEP_S
        t = float(ap["t"])
        noise = np.random.default_rng([11, int(t)])
        pm_out = engine.outdoor.true_pm(t)
        for rid, room in rooms.items():
            if rid in last:
                engine.ingest(rid, last[rid], infer=False)
            room.sensor.rng = noise
            kids, adults = engine.occupants_at(rid, ist_minute(t))
            room.step(STEP_S, pm_out, 450.0, kids, adults)
            co2, pm = room.sensor.read(room.co2, room.pm)
            last[rid] = {"ts": t, "co2": co2, "pm25": pm, "simulated": True}
        steps += 1
    for rid, reading in last.items():
        engine.ingest(rid, reading, infer=True)  # fit the CO₂ curve once, on the newest reading
    return steps


def _teacher(engine: Any, ap: Item, rooms: dict[str, TrueRoom]) -> None:
    """Whoever is watching is the teacher. Once an instruction is tapped (or its tap window passes and it
    moves to verification), the true window changes."""
    seen: dict[str, str] = dict(ap.get("seen") or {})
    for rid, room in rooms.items():
        st = runtime.store().get(f"ROOM#{rid}", "STATE")
        sk = (st or {}).get("open_nudge")
        nudge = runtime.store().get(f"ROOM#{rid}", sk) if sk else None
        if not nudge:
            continue
        status = nudge["state"]["status"]
        key = f"{nudge['nudge_id']}:{status}"
        previous = seen.get(rid, "")
        if previous == key:
            continue
        seen[rid] = key
        if status == "verifying" and not previous.endswith(":verifying"):
            window, purifier = Window(nudge["action"]["window"]), Purifier(nudge["action"]["purifier"])
            follow_up = previous.endswith(":follow_up")
            if window == Window.OPEN_BOTH and not follow_up:
                ap["opens"] = int(ap.get("opens", 0)) + 1
                if int(ap["opens"]) == 1:
                    window = Window.OPEN_ONE  # the scripted mistake: only the road side opens
            room.set(window, purifier, float(ap["t"]))
    ap["seen"] = seen


def _fresh_morning(metrics: Any, now_real: float) -> tuple[Any, Item, dict[str, TrueRoom]]:
    item = runtime.reset_demo(SCENARIO, SPEED)
    start = float(item["anchor_sim"])
    # the clock starts 12 minutes into the morning; the readings for those minutes are filled in below
    item.update(anchor_sim=start + WARMUP_MIN * 60, anchor_real=time.time())
    runtime.store().put("SIM", "CLOCK", item)
    engine = runtime.engine(metrics)
    ap: Item = {"last_real": now_real, "t": start, "seen": {}, "opens": 0, "epoch": item["epoch"]}
    rooms = _rooms(engine, {})
    pm0 = engine.outdoor.true_pm(start)
    for room in rooms.values():
        room.co2, room.pm = 520.0, 0.55 * pm0
    _advance(engine, ap, rooms, start + WARMUP_MIN * 60, max_steps=WARMUP_MIN * 2 + 2)
    return engine, ap, rooms


def pulse(metrics: Any = None) -> Item:
    now_real = time.time()
    store = runtime.store()
    ap = store.get(*KEY) or {}
    if now_real - float(ap.get("external_at", 0)) < EXTERNAL_HOLD_S:
        return {"state": "external"}
    used = int((store.get(*budget_key(now_real)) or {}).get("executions", 0))
    if used >= MONTHLY_EXECUTION_CAP:
        return {"state": "resting", "executions": used, "cap": MONTHLY_EXECUTION_CAP}
    last = ap.get("last_real")
    if last is not None and now_real - float(last) < MIN_GAP_S:
        return {"state": "running", "stepped": 0}
    if not _claim(None if last is None else float(last), now_real):
        return {"state": "running", "stepped": 0}

    clock = runtime.clock_item()
    stale = last is None or now_real - float(last) > IDLE_RESTART_S
    foreign = clock is None or clock.get("scenario") != SCENARIO or clock.get("epoch") != ap.get("epoch")
    fresh = stale or foreign or not ap.get("rooms")
    if not fresh:
        engine = runtime.engine(metrics)
        fresh = ist_minute(engine.clock.now()) >= DAY_END_MIN  # school is over: start the morning again
    if fresh:
        engine, ap, rooms = _fresh_morning(metrics, now_real)
        steps = WARMUP_MIN * 2
    else:
        ap["last_real"] = now_real
        rooms = _rooms(engine, ap.get("rooms") or {})
        steps = _advance(engine, ap, rooms, engine.clock.now(), MAX_STEPS)
    engine.tick()
    _teacher(engine, ap, rooms)
    _save(ap, rooms)
    return {
        "state": "running",
        "stepped": steps,
        "fresh": fresh,
        "clock": engine.clock_view(),
        "executions": used,
    }
