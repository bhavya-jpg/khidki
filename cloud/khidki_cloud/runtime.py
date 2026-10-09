"""Builds the engine inside Lambda: DynamoDB store, the shared demo clock, outdoor data, Cedar, and the Step
Functions wiring. Module-level objects survive between warm invocations."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import boto3

from khidki_core.clock import ClockMode, ClockState, SimClock
from khidki_services.dynamo import DynamoStore
from khidki_services.engine import Engine
from khidki_services.outdoor import LiveOutdoor, OutdoorEvent, ReplayOutdoor
from khidki_services.policy import CedarPolicyEngine
from khidki_services.seed import DEMO_SCHOOL
from khidki_services.store import Item

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
TABLE = os.environ.get("KHIDKI_TABLE", "Khidki")
STATE_MACHINE_ARN = os.environ.get("KHIDKI_NUDGE_SM", "")
SCENARIOS_FILE = Path(__file__).parent / "scenarios.json"

_store: DynamoStore | None = None
_engine: Engine | None = None
_engine_key: tuple[Any, ...] | None = None
_policy: CedarPolicyEngine | None = None
_sfn: Any = None
_ssm_cache: dict[str, tuple[str, float]] = {}
_metrics: Any = None


def store() -> DynamoStore:
    global _store
    if _store is None:
        _store = DynamoStore(TABLE)
    return _store


def sfn() -> Any:
    global _sfn
    if _sfn is None:
        _sfn = boto3.client("stepfunctions", region_name=REGION)
    return _sfn


def ssm_param(name: str, ttl_s: float = 300) -> str:
    hit = _ssm_cache.get(name)
    if hit and time.time() - hit[1] < ttl_s:
        return hit[0]
    value = boto3.client("ssm", region_name=REGION).get_parameter(Name=name, WithDecryption=True)[
        "Parameter"
    ]["Value"]
    _ssm_cache[name] = (value, time.time())
    return str(value)


def scenarios() -> dict[str, Item]:
    if SCENARIOS_FILE.exists():
        return {s["name"]: s for s in json.loads(SCENARIOS_FILE.read_text())}
    import dataclasses

    from khidki_sim import scenario as sc  # local runs: read the YAML directly

    return {n: dataclasses.asdict(sc.load(n)) for n in sc.list_scenarios()}


def clock_item() -> Item | None:
    return store().get("SIM", "CLOCK")


def _clock(item: Item | None) -> SimClock:
    if not item or item.get("mode") != "demo":
        return SimClock()
    return SimClock(
        ClockState(
            ClockMode.DEMO,
            anchor_real=float(item["anchor_real"]),
            anchor_sim=float(item["anchor_sim"]),
            speed=float(item["speed"]),
            paused=bool(item.get("paused", False)),
        )
    )


def _outdoor(item: Item | None) -> Any:
    if item and item.get("mode") == "demo":
        events = []
        for e in item.get("events", []):
            h, m = (int(x) for x in str(e["at"]).split(":"))
            events.append(
                OutdoorEvent(
                    start_min=h * 60 + m,
                    end_min=h * 60 + m + int(e["duration_min"]),
                    factor=float(e["factor"]),
                )
            )
        return ReplayOutdoor(date=item["date"], events=events)
    return LiveOutdoor()


def safe_execution_name(nudge_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", nudge_id)[:70] + f"-{int(time.time())}"


def engine(metrics: Any | None = None) -> Engine:
    """The engine for this invocation, re-pointed at the current demo clock."""
    global _engine, _engine_key, _policy, _metrics
    _metrics = metrics
    item = clock_item()
    key = (item or {}).get("scenario"), (item or {}).get("date"), (item or {}).get("epoch")
    if _policy is None:
        _policy = CedarPolicyEngine(DEMO_SCHOOL)
    if _engine is None or key != _engine_key:
        _engine = Engine(store(), _clock(item), _outdoor(item), policy=_policy, external_nudges=True)
        _engine_key = key

        def start_nudge(room_id: str, nudge: Item) -> None:
            if not STATE_MACHINE_ARN:
                return
            assert _engine is not None
            sfn().start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=safe_execution_name(nudge["nudge_id"]),
                input=json.dumps(
                    {"nudge_id": nudge["nudge_id"], "room_id": room_id, **_engine.nudge_seconds()}
                ),
            )
            if _metrics is not None:
                _metrics.add_metric(name="NudgesIssued", unit="Count", value=1)

        def return_tap(token: str, output: Item) -> None:
            try:
                sfn().send_task_success(taskToken=token, output=json.dumps(output))
            except sfn().exceptions.TaskTimedOut:
                pass  # Step Functions already gave up waiting and moved on to verification
            except sfn().exceptions.InvalidToken:
                pass

        _engine.on_nudge.append(start_nudge)
        _engine.task_notifier = return_tap
    else:
        _engine.clock = _clock(item)
    if store().get(f"SCHOOL#{DEMO_SCHOOL.school_id}", "META") is None:
        _engine.seed()
    return _engine


def reset_demo(scenario_name: str, speed: float | None = None) -> Item:
    """Start a scenario: wipe the school's rooms, re-seed, and anchor the shared demo clock."""
    sc = scenarios()[scenario_name]
    s = store()
    for pk in [f"SCHOOL#{DEMO_SCHOOL.school_id}", *[f"ROOM#{r.room_id}" for r in DEMO_SCHOOL.rooms]]:
        with s.table.batch_writer() as batch:
            for it in s.query(pk):
                batch.delete_item(Key={"pk": it["pk"], "sk": it["sk"]})
    clock = SimClock()
    clock.start_demo(sc["date"], sc["start"], float(speed or sc["speed"]))
    st = clock.state
    item = {
        "mode": "demo",
        "anchor_real": st.anchor_real,
        "anchor_sim": st.anchor_sim,
        "speed": st.speed,
        "paused": False,
        "scenario": scenario_name,
        "date": sc["date"],
        "events": sc.get("events", []),
        "teacher_mode": sc["teacher"]["mode"],
        "epoch": time.time(),
    }
    s.put("SIM", "CLOCK", item)
    engine().seed()
    return item


def update_clock(**changes: Any) -> Item:
    item = clock_item()
    if not item:
        raise KeyError("No demo running. Start a scenario first.")
    clock = _clock(item)
    if "speed" in changes:
        clock.set_speed(float(changes["speed"]))
    if "paused" in changes:
        clock.pause(bool(changes["paused"]))
    st = clock.state
    item.update(anchor_real=st.anchor_real, anchor_sim=st.anchor_sim, speed=st.speed, paused=st.paused)
    store().put("SIM", "CLOCK", item)
    return item
