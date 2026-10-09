"""Replay days: real Delhi outdoor air (CAMS via Open-Meteo) for 2025 school days, cached in fixtures/.

A replay day drives the simulator, the benchmark and the Lab. Indoor air is always simulated; outdoor air is
real. Every surface that shows a replay day says so.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np

from khidki_core.aqi import pm25_subindex
from khidki_core.physics import DriveSeries
from khidki_core.schemas import RoomParams
from khidki_core.timetable import PLAN_DT_MIN, occupancy, plan_grid
from khidki_data.openmeteo import Hourly

FIXTURES = Path(__file__).parent / "fixtures" / "replay"
DEMO_LAT, DEMO_LON = 28.6469, 77.3152  # East Delhi, near Anand Vihar


@dataclass(frozen=True)
class ReplayDay:
    date: str
    hourly: Hourly

    def series(self, name: str) -> np.ndarray:
        return np.array([np.nan if v is None else v for v in self.hourly.values[name]], dtype=np.float64)

    @property
    def hour_min(self) -> np.ndarray:
        return np.array([int(t[11:13]) * 60 for t in self.hourly.time], dtype=np.float64)

    @property
    def mean_pm25_24h(self) -> float:
        return float(np.nanmean(self.series("pm2_5")))

    @property
    def aqi(self) -> int:
        return pm25_subindex(self.mean_pm25_24h)

    def school_hours_pm25(self) -> float:
        h = self.hour_min
        x = self.series("pm2_5")
        return float(np.nanmean(x[(h >= 7 * 60) & (h <= 13 * 60)]))


def list_days() -> list[str]:
    return sorted(p.stem for p in FIXTURES.glob("20*.json"))


@cache
def load_day(date: str) -> ReplayDay:
    path = FIXTURES / f"{date}.json"
    if not path.exists():
        raise KeyError(f"no replay day {date}; run `python tasks.py fetch-replay`")
    return ReplayDay(date=date, hourly=Hourly.from_json(json.loads(path.read_text())))


def _interp_series(hour_min: np.ndarray, x: np.ndarray, t_min: np.ndarray, default: float) -> np.ndarray:
    ok = np.isfinite(x)
    if not ok.any():
        return np.full(len(t_min), default)
    return np.asarray(np.interp(t_min, hour_min[ok], x[ok]), dtype=np.float64)


def build_drive(
    hour_min: np.ndarray,
    pm25: np.ndarray,
    temp: np.ndarray,
    co2: np.ndarray,
    params: RoomParams,
    *,
    assembly_outdoor: bool = False,
    recess_outdoor: bool = True,
    pe_period: int | None = 6,
    pe_outdoor: bool = False,
    start_min: int | None = None,
    dt_min: int = PLAN_DT_MIN,
) -> DriveSeries:
    """Hourly outdoor series interpolated to the plan grid, with occupancy from the timetable and today's
    activity decisions. Open-Meteo hourly values are hour-beginning; linear interpolation between them is a
    reasonable 5-minute proxy."""
    t = plan_grid(start_min=start_min) if start_min is not None else plan_grid()
    if dt_min != PLAN_DT_MIN:
        t = np.arange(t[0], t[-1] + PLAN_DT_MIN, dt_min, dtype=np.int64)
    kids, adults = occupancy(
        t,
        params.students,
        params.adults,
        assembly_outdoor=assembly_outdoor,
        recess_outdoor=recess_outdoor,
        pe_period=pe_period,
        pe_outdoor=pe_outdoor,
    )
    c = _interp_series(hour_min, co2, t, 450.0)
    c = np.where((c > 350) & (c < 700), c, 450.0)
    return DriveSeries(
        t_min=t,
        dt_min=dt_min,
        pm_out=np.maximum(_interp_series(hour_min, pm25, t, 150.0), 0.0),
        co2_out=c,
        temp_out=_interp_series(hour_min, temp, t, 20.0),
        n_children=kids,
        n_adults=adults,
    )


def drive_for_day(day: ReplayDay, params: RoomParams, **kwargs: Any) -> DriveSeries:
    return build_drive(
        day.hour_min,
        day.series("pm2_5"),
        day.series("temperature_2m"),
        day.series("carbon_dioxide"),
        params,
        **kwargs,
    )
