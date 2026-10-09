"""DynamoStore behaves like MemoryStore (moto, no AWS account needed)."""

import os

import boto3
import pytest
from moto import mock_aws

from khidki_core.clock import SimClock
from khidki_core.optimizer import Grid
from khidki_services.dynamo import DynamoStore, create_table
from khidki_services.engine import Engine
from khidki_services.outdoor import ReplayOutdoor
from khidki_services.store import MemoryStore


@pytest.fixture
def stores():  # type: ignore[no-untyped-def]
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="ap-south-1")
        create_table("KhidkiTest", ddb)
        yield [MemoryStore(), DynamoStore("KhidkiTest", ddb)]


def test_same_behaviour_as_memory_store(stores) -> None:  # type: ignore[no-untyped-def]
    results = []
    for s in stores:
        s.put("ROOM#6B", "STATE", {"co2": 1620.5, "pm25": None, "nested": {"a": [1, 2.5, "x"]}, "ok": True})
        for i in range(5):
            s.put("ROOM#6B", f"TEL#2025-11-18T0{i}:00:00Z", {"ts": 1000.0 + i, "co2": 600 + i})
        s.put("ROOM#6B", "NUDGE#2025-11-18T03:00:00Z", {"x": 1})
        results.append(
            (
                s.get("ROOM#6B", "STATE"),
                [r["co2"] for r in s.query("ROOM#6B", "TEL#")],
                [r["co2"] for r in s.query("ROOM#6B", "TEL#", limit=2, newest_first=True)],
                [r["co2"] for r in s.query("ROOM#6B", "TEL#", sk_from="TEL#2025-11-18T03")],
                s.get("ROOM#6B", "missing"),
            )
        )
        s.delete("ROOM#6B", "STATE")
        assert s.get("ROOM#6B", "STATE") is None
    mem, dyn = results
    assert {k: v for k, v in mem[0].items()} == {k: v for k, v in dyn[0].items()}
    assert mem[1:] == dyn[1:]
    assert mem[1] == [600, 601, 602, 603, 604] and mem[2] == [604, 603] and mem[3] == [603, 604]


def test_engine_runs_on_dynamodb(stores) -> None:  # type: ignore[no-untyped-def]
    t = [1_000_000.0]
    clock = SimClock(real_time=lambda: t[0])
    clock.start_demo("2025-11-18", "08:00", 1.0)
    engine = Engine(stores[1], clock, ReplayOutdoor("2025-11-18"), grid=Grid(co2_step=50, pm_step=5))
    engine.seed()
    engine.ingest("6B", {"ts": clock.now(), "co2": 1500.0, "pm25": 90.0})
    engine.tick()
    view = engine.room_now("6B")
    assert view["indoor"]["co2"] > 0 and view["simulated"]
    assert engine.plan_view("6B") is not None
