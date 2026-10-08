"""School-day timetable and classroom occupancy.

Demo timetable (winter timing): assembly 07:30 to 07:50, four 35-minute periods, recess 10:10 to 10:40,
four more periods, dismissal 13:00. The planning day runs 07:00 to 13:30 in 5-minute steps.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from khidki_core.physics import FloatArray, IntArray

DAY_START_MIN = 7 * 60
DAY_END_MIN = 13 * 60 + 30
PLAN_DT_MIN = 5


@dataclass(frozen=True)
class Slot:
    name: str
    kind: str  # "assembly" | "period" | "recess"
    start_min: int
    end_min: int


def hhmm(minute_of_day: int) -> str:
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


def parse_hhmm(text: str) -> int:
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def default_timetable() -> tuple[Slot, ...]:
    slots = [Slot("Assembly", "assembly", parse_hhmm("07:30"), parse_hhmm("07:50"))]
    t = parse_hhmm("07:50")
    for p in range(1, 9):
        if p == 5:
            slots.append(Slot("Recess", "recess", t, t + 30))
            t += 30
        slots.append(Slot(f"Period {p}", "period", t, t + 35))
        t += 35
    return tuple(slots)


def slot_at(minute: int, timetable: tuple[Slot, ...]) -> Slot | None:
    for s in timetable:
        if s.start_min <= minute < s.end_min:
            return s
    return None


def plan_grid(
    start_min: int = DAY_START_MIN, end_min: int = DAY_END_MIN, dt_min: int = PLAN_DT_MIN
) -> IntArray:
    return np.arange(start_min, end_min, dt_min, dtype=np.int64)


def occupancy(
    t_min: IntArray,
    students: int,
    adults: int = 1,
    timetable: tuple[Slot, ...] | None = None,
    assembly_outdoor: bool = True,
    recess_outdoor: bool = True,
    pe_period: int | None = None,
    pe_outdoor: bool = True,
) -> tuple[FloatArray, FloatArray]:
    """Children and adults in the room at each time. When an outdoor activity is moved indoors by policy,
    the class stays in its room."""
    tt = timetable or default_timetable()
    kids = np.zeros(len(t_min))
    grown = np.zeros(len(t_min))
    for i, m in enumerate(t_min):
        s = slot_at(int(m), tt)
        if s is None:
            continue
        out = (
            (s.kind == "assembly" and assembly_outdoor)
            or (s.kind == "recess" and recess_outdoor)
            or (pe_period is not None and s.name == f"Period {pe_period}" and pe_outdoor)
        )
        if not out:
            kids[i] = students
            grown[i] = adults
    return kids, grown
