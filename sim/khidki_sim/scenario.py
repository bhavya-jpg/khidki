"""Scenario files (sim/scenarios/*.yaml): which day, how fast, how the teacher behaves, injected events."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


@dataclass(frozen=True)
class TeacherSpec:
    mode: str = "auto"  # "auto" | "ui"
    p_follow: float = 0.85
    delay_s: tuple[float, float] = (30.0, 120.0)
    partial_first_open: bool = False
    fake_confirm_first: bool = False
    cant_first: str | None = None


@dataclass(frozen=True)
class Event:
    at: str
    kind: str
    factor: float = 1.0
    duration_min: int = 60


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    date: str
    start: str
    speed: float
    teacher: TeacherSpec
    rooms: tuple[str, ...] = ("6B", "3A")
    events: tuple[Event, ...] = field(default_factory=tuple)
    seed: int = 7


def list_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIOS.glob("*.yaml"))


def load(name: str) -> Scenario:
    raw: dict[str, Any] = yaml.safe_load((SCENARIOS / f"{name}.yaml").read_text())
    t = raw.get("teacher", {})
    teacher = TeacherSpec(
        mode=t.get("mode", "auto"),
        p_follow=float(t.get("p_follow", 0.85)),
        delay_s=tuple(t.get("delay_s", (30, 120))),  # type: ignore[arg-type]
        partial_first_open=bool(t.get("partial_first_open", False)),
        fake_confirm_first=bool(t.get("fake_confirm_first", False)),
        cant_first=t.get("cant_first"),
    )
    return Scenario(
        name=raw["name"],
        description=raw.get("description", ""),
        date=str(raw["date"]),
        start=str(raw.get("start", "07:00")),
        speed=float(raw.get("speed", 10)),
        teacher=teacher,
        rooms=tuple(raw.get("rooms", ("6B", "3A"))),
        events=tuple(Event(**e) for e in raw.get("events", [])),
        seed=int(raw.get("seed", 7)),
    )
