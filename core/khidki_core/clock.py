"""SimClock: one notion of "now" for every component.

LIVE: real time. DEMO: anchor_sim + (real_now − anchor_real) × speed, so a recorded demo can replay a real
2025 day at 10× while the planner, nudge waits and UI all agree on the time. The UI shows a SIM badge
whenever the clock is not live.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum

IST = dt.timezone(dt.timedelta(hours=5, minutes=30), name="IST")


class ClockMode(StrEnum):
    LIVE = "live"
    DEMO = "demo"


@dataclass(frozen=True)
class ClockState:
    mode: ClockMode = ClockMode.LIVE
    anchor_real: float = 0.0
    anchor_sim: float = 0.0
    speed: float = 1.0
    paused: bool = False


class SimClock:
    def __init__(self, state: ClockState | None = None, real_time: Callable[[], float] | None = None) -> None:
        self._state = state or ClockState()
        self._real = real_time or time.time

    @property
    def state(self) -> ClockState:
        return self._state

    @property
    def is_simulated(self) -> bool:
        return self._state.mode == ClockMode.DEMO

    @property
    def speed(self) -> float:
        return self._state.speed if self.is_simulated else 1.0

    def now(self) -> float:
        """Epoch seconds (simulated in DEMO mode)."""
        s = self._state
        if s.mode == ClockMode.LIVE:
            return float(self._real())
        if s.paused:
            return s.anchor_sim
        return s.anchor_sim + (float(self._real()) - s.anchor_real) * s.speed

    def now_ist(self) -> dt.datetime:
        return dt.datetime.fromtimestamp(self.now(), tz=IST)

    def minute_of_day(self) -> int:
        n = self.now_ist()
        return n.hour * 60 + n.minute

    def date(self) -> str:
        return self.now_ist().date().isoformat()

    def real_seconds(self, sim_seconds: float) -> float:
        """How long to really wait for `sim_seconds` of simulated time (Step Functions Wait uses this)."""
        return sim_seconds / self.speed

    def start_demo(self, date: str, hhmm: str, speed: float) -> None:
        h, m = (int(x) for x in hhmm.split(":"))
        d = dt.date.fromisoformat(date)
        sim = dt.datetime(d.year, d.month, d.day, h, m, tzinfo=IST).timestamp()
        self._state = ClockState(ClockMode.DEMO, anchor_real=float(self._real()), anchor_sim=sim, speed=speed)

    def set_speed(self, speed: float) -> None:
        """Re-anchor so time doesn't jump when the speed changes."""
        now = self.now()
        self._state = replace(self._state, anchor_real=float(self._real()), anchor_sim=now, speed=speed)

    def pause(self, paused: bool = True) -> None:
        now = self.now()
        self._state = replace(self._state, anchor_real=float(self._real()), anchor_sim=now, paused=paused)

    def go_live(self) -> None:
        self._state = ClockState()


def ist_epoch(date: str, minute_of_day: int) -> float:
    d = dt.date.fromisoformat(date)
    return dt.datetime(
        d.year, d.month, d.day, minute_of_day // 60, minute_of_day % 60, tzinfo=IST
    ).timestamp()


def ist_minute(epoch_s: float) -> float:
    """Minute of day (IST, fractional) for an epoch time."""
    t = dt.datetime.fromtimestamp(epoch_s, tz=IST)
    return t.hour * 60 + t.minute + t.second / 60.0
