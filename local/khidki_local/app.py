"""FastAPI app for local mode. Same engine and simulator as the cloud; in-memory store; a background loop
advances the simulated day.

Run: python tasks.py local   (or: uv run uvicorn khidki_local.app:app --port 8000)
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import threading
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from khidki_core.clock import SimClock
from khidki_data.openmeteo import ATTRIBUTION
from khidki_services.engine import Engine
from khidki_services.store import MemoryStore
from khidki_sim import scenario as scenarios
from khidki_sim.driver import SimDriver, outdoor_for

VERSION = "0.2.0"


class Runtime:
    """Holds the engine and simulator; one lock serialises the loop and API calls."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.running = False
        self.load(
            os.environ.get("KHIDKI_SCENARIO", "severe_morning"),
            speed=float(os.environ.get("KHIDKI_SPEED", "0")) or None,
        )

    def load(self, name: str, speed: float | None = None) -> None:
        with self.lock:
            sc = scenarios.load(name)
            self.scenario = sc
            self.clock = SimClock()
            self.clock.start_demo(sc.date, sc.start, speed or sc.speed)
            outdoor = outdoor_for(sc)
            self.engine = Engine(MemoryStore(), self.clock, outdoor)
            self.engine.seed()
            self.sim = SimDriver.start_of_day(self.engine, sc, outdoor)
            self.running = True

    def step(self) -> None:
        with self.lock:
            if not self.running:
                return
            self.sim.advance(self.clock.now())
            self.engine.tick()


RT: Runtime | None = None


def rt() -> Runtime:
    global RT
    if RT is None:
        RT = Runtime()
    return RT


async def _loop() -> None:
    while True:
        await asyncio.to_thread(rt().step)
        await asyncio.sleep(1.0)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_loop()) if os.environ.get("KHIDKI_NO_LOOP") != "1" else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Khidki (local mode)", version=VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AckBody(BaseModel):
    result: Literal["done", "cant"]
    reason: Literal["cold", "noise", "rain", "exam"] | None = None


class SimControl(BaseModel):
    action: Literal["scenario", "speed", "pause", "resume", "reset"]
    scenario: str | None = None
    speed: float | None = Field(default=None, gt=0, le=120)


class Reading(BaseModel):
    room_id: str
    ts: float | None = None
    co2: float = Field(gt=0, lt=10000)
    pm25: float | None = Field(default=None, ge=0, lt=2000)
    simulated: bool = True


@app.get("/v1/health")
def health() -> dict[str, Any]:
    r = rt()
    with r.lock:
        return {
            "ok": True,
            "version": VERSION,
            "mode": "local",
            "clock": r.engine.clock_view(),
            "scenario": r.scenario.name,
            "attribution": ATTRIBUTION,
        }


@app.get("/v1/rooms/{room_id}/now")
def room_now(room_id: str) -> dict[str, Any]:
    r = rt()
    with r.lock:
        try:
            return r.engine.room_now(room_id)
        except KeyError as exc:
            raise HTTPException(404, f"No room {room_id}") from exc


@app.get("/v1/rooms/{room_id}/plan")
def room_plan(room_id: str) -> dict[str, Any]:
    r = rt()
    with r.lock:
        plan = r.engine.plan_view(room_id)
    if plan is None:
        raise HTTPException(404, "No plan yet. Plans start at 07:00.")
    return plan


@app.post("/v1/rooms/{room_id}/replan")
def replan(room_id: str) -> dict[str, Any]:
    r = rt()
    with r.lock:
        r.engine.replan(room_id, reason="requested")
        return r.engine.plan_view(room_id) or {}


@app.post("/v1/nudges/{nudge_id}/ack")
def ack(nudge_id: str, body: AckBody) -> dict[str, Any]:
    r = rt()
    with r.lock:
        try:
            n = r.engine.ack(nudge_id, body.result, body.reason)
        except KeyError as exc:
            raise HTTPException(404, "That instruction has already finished.") from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"nudge_id": n["nudge_id"], "state": n["state"]}


@app.get("/v1/schools/{school_id}/today")
def school_today(school_id: str) -> dict[str, Any]:
    r = rt()
    with r.lock:
        if school_id != r.engine.school.school_id:
            raise HTTPException(404, f"No school {school_id}")
        return r.engine.school_today()


@app.get("/v1/sim/scenarios")
def list_scenarios() -> list[dict[str, Any]]:
    out = []
    for name in scenarios.list_scenarios():
        sc = scenarios.load(name)
        out.append(
            {"name": sc.name, "description": sc.description, "date": sc.date, "teacher": sc.teacher.mode}
        )
    return out


@app.post("/v1/sim/control")
def sim_control(body: SimControl) -> dict[str, Any]:
    r = rt()
    if body.action == "scenario":
        if body.scenario not in scenarios.list_scenarios():
            raise HTTPException(404, f"No scenario {body.scenario}")
        r.load(body.scenario, body.speed)
    elif body.action == "reset":
        r.load(r.scenario.name, body.speed)
    with r.lock:
        if body.action == "speed" and body.speed:
            r.clock.set_speed(body.speed)
        elif body.action == "pause":
            r.clock.pause(True)
        elif body.action == "resume":
            r.clock.pause(False)
        return {"scenario": r.scenario.name, "clock": r.engine.clock_view()}


@app.post("/ingest")
def ingest(reading: Reading) -> dict[str, Any]:
    """For an external simulator or a real sensor node on the LAN."""
    r = rt()
    with r.lock:
        try:
            r.engine.room_cfg(reading.room_id)
        except KeyError as exc:
            raise HTTPException(404, f"No room {reading.room_id}") from exc
        item = r.engine.ingest(reading.room_id, reading.model_dump())
        return {"stored": True, "ts": item["ts"]}
