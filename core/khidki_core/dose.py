"""Exposure and cost metrics (docs/physics.md §dose).

All per-child metrics count only time the children are in the room.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np

from khidki_core.physics import ActionArrays, DriveSeries, FloatArray, IntArray, SimResult
from khidki_core.schemas import Kpis

DEFAULT_IR_M3_H = 0.5
"""Inhalation rate of a seated child, m³/h (US EPA Exposure Factors Handbook, ch. 6). Headline claims are
relative, so they don't depend on this value."""

COLD_BELOW_C = 18.0


def co2_points_rate(co2: FloatArray | float) -> FloatArray:
    """Discomfort points per occupied minute: 0 below 1,000 ppm, 1 at 1,500, 4 at 2,000, then +10 per
    1,000 ppm."""
    c = np.asarray(co2, dtype=np.float64)
    return np.select(
        [c < 1000, c < 1500, c < 2000],
        [np.zeros_like(c), (c - 1000) / 500, 1 + 3 * (c - 1500) / 500],
        default=4 + 10 * (c - 2000) / 1000,
    )


def cold_rate(open_fraction: FloatArray | float, temp_out: FloatArray | float) -> FloatArray:
    """Cold-exposure proxy per minute: open fraction × degrees below 18 °C outside."""
    return np.asarray(open_fraction) * np.maximum(0.0, COLD_BELOW_C - np.asarray(temp_out))


def count_changes(action_idx: IntArray | list[int], prev_idx: int | None = None) -> int:
    idx = list(np.asarray(action_idx, dtype=np.int64))
    if prev_idx is not None:
        idx = [prev_idx, *idx]
    return int(sum(1 for a, b in pairwise(idx) if a != b))


def compute_kpis(
    drive: DriveSeries,
    sim: SimResult,
    aa: ActionArrays,
    action_idx: IntArray | list[int],
    prev_idx: int | None = None,
    ir_m3_h: float = DEFAULT_IR_M3_H,
) -> Kpis:
    idx = np.asarray(action_idx, dtype=np.int64)
    kids = drive.children_present
    dt_min = float(drive.dt_min)
    occ_minutes = float(kids.sum()) * dt_min
    pm_dose = float(np.sum(sim.pm_mean * kids) * ir_m3_h * drive.dt_h)
    return Kpis(
        pm_dose_ug=round(pm_dose, 2),
        co2_min_over_1000=float(np.sum((sim.co2_mean > 1000) & kids) * dt_min),
        co2_min_over_1500=float(np.sum((sim.co2_mean > 1500) & kids) * dt_min),
        co2_points=round(float(np.sum(co2_points_rate(sim.co2_mean) * kids) * dt_min), 2),
        cold_deg_min=round(
            float(np.sum(cold_rate(aa.open_fraction[idx], drive.temp_out) * kids) * dt_min), 2
        ),
        window_changes=count_changes(idx, prev_idx),
        mean_pm_occupied=round(float(np.sum(sim.pm_mean * kids) * dt_min / occ_minutes), 1)
        if occ_minutes
        else 0.0,
        max_co2=round(float(np.max(sim.co2_mean[kids])) if kids.any() else float(sim.co2[0]), 0),
    )
