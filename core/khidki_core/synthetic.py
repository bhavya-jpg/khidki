"""Synthetic outdoor days for tests and the Lab's offline default. Real replay days live in khidki_data."""

from __future__ import annotations

import numpy as np

from khidki_core.physics import DriveSeries
from khidki_core.schemas import RoomParams
from khidki_core.timetable import PLAN_DT_MIN, occupancy, plan_grid


def severe_morning(
    params: RoomParams | None = None,
    pe_period: int | None = 6,
    outdoor_allowed: bool = False,
    dt_min: int = PLAN_DT_MIN,
) -> DriveSeries:
    """A Delhi-like post-monsoon severe day: PM2.5 ~260 at 07:00 under a shallow boundary layer, easing to
    ~120 by early afternoon with a brief late-morning dip; cold morning warming to ~24 °C."""
    p = params or RoomParams()
    t = plan_grid()
    h = (t - 7 * 60) / 60.0
    pm_out = 260 - 22 * h - 35 * np.exp(-((h - 3.6) ** 2) / 0.3) + 12 * np.exp(-((h - 5.5) ** 2) / 0.2)
    temp = 13 + 11 * (1 - np.exp(-h / 3.0))
    kids, adults = occupancy(
        t,
        p.students,
        p.adults,
        assembly_outdoor=outdoor_allowed,
        recess_outdoor=True,
        pe_period=pe_period,
        pe_outdoor=outdoor_allowed,
    )
    drive = DriveSeries(
        t_min=t,
        dt_min=PLAN_DT_MIN,
        pm_out=np.asarray(pm_out, dtype=np.float64),
        co2_out=np.full(len(t), 450.0),
        temp_out=np.asarray(temp, dtype=np.float64),
        n_children=kids,
        n_adults=adults,
    )
    return drive if dt_min == PLAN_DT_MIN else drive.resample(dt_min)
