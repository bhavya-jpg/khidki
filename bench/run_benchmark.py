"""Benchmark: Khidki vs four baselines on every cached 2025 Delhi replay day.

Simulation on a modelled classroom driven by real outdoor air (CAMS via Open-Meteo). Not a field trial.

Honesty choices:
- The "true" room has different physics from the twin Khidki plans with (hidden_truth vs defaults), so
  Khidki is planning with a wrong model, as it would before its first nightly fingerprint.
- Khidki and the CO₂ alarm get the same teacher: acts on a request 70% of the time, after 1 to 3 minutes.
  KHIDKI_100 is the upper bound with a teacher who always acts.
- Khidki re-plans every 30 minutes from the measured state and respects the 6-request daily budget, counting
  every request (including ones the teacher ignored).
- Everything is simulated at 1-minute resolution on the true room.

Usage: python tasks.py bench [--days N] [--workers N]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from khidki_core import dose
from khidki_core.baselines import run_policy, standard_baselines
from khidki_core.optimizer import CostConfig, Grid, optimize
from khidki_core.physics import (
    ActionArrays,
    DriveSeries,
    SimResult,
    action_arrays,
    co2_coeffs,
    co2_source_ppm_per_h,
    pm_coeffs,
    relax,
)
from khidki_core.schemas import PROFILE_ALPHA, Profile, RoomParams
from khidki_core.timetable import default_timetable
from khidki_data.replay import drive_for_day, list_days, load_day
from khidki_sim.room import hidden_truth

RESULTS = Path(__file__).parent / "results"
GRID = Grid(co2_step=50.0, pm_step=4.0)  # coarser than live planning, to keep 48 days × 2 rooms quick
REPLAN_EVERY_MIN = 30
MAX_REQUESTS = 6
ROOMS = {
    "no_purifier": RoomParams(students=44, has_purifier=False),
    "purifier": RoomParams(students=38, has_purifier=True),
}
POLICIES = ["ALWAYS_CLOSED", "ALWAYS_OPEN", "CO2_ALARM", "TEMPERATURE_TEACHER", "KHIDKI", "KHIDKI_100"]
# Lungs-first sweep: how Khidki trades CO₂ for PM as the PM weight α rises (Balanced is α = 0.5).
SWEEP_ALPHAS = (0.6, 0.7, 0.8, 0.9)
SWEEP = [f"KHIDKI_a{a:.1f}" for a in SWEEP_ALPHAS]


def stable_seed(*parts: str) -> int:
    """Python's hash() is randomised per process; seeds must be reproducible across runs."""
    return zlib.crc32("|".join(parts).encode())


def activity_flags(day_date: str) -> dict[str, Any]:
    """Same rule as Cedar policy S2: outdoor activities move indoors if forecast PM2.5 in the hour before or
    during them exceeds 90 µg/m³ (CPCB 'Poor')."""
    day = load_day(day_date)
    pm, h = day.series("pm2_5"), day.hour_min

    def outdoor(start: int, end: int) -> bool:
        m = (h >= start - 59) & (h < end)
        return bool(np.nanmax(pm[m]) <= 90) if m.any() else True

    pe = next(s for s in default_timetable() if s.name == "Period 6")
    return {
        "assembly_outdoor": outdoor(450, 470),
        "recess_outdoor": outdoor(610, 640),
        "pe_period": 6,
        "pe_outdoor": outdoor(pe.start_min, pe.end_min),
    }


def step_true(
    true: RoomParams, aa: ActionArrays, a: int, c: float, p: float, d1: DriveSeries, i: int, src: np.ndarray
) -> tuple[float, float, float, float]:
    a_c, b_c = co2_coeffs(aa.lam[a], d1.co2_out[i], src[i])
    a_p, b_p = pm_coeffs(aa.lam[a], aa.pen[a], aa.q_eff_m3_h[a], d1.pm_out[i], true)
    c_end, c_mean = relax(c, a_c, b_c, d1.dt_h)
    p_end, p_mean = relax(p, a_p, b_p, d1.dt_h)
    return float(c_end), float(c_mean), float(p_end), float(p_mean)


def run_khidki(
    model: RoomParams,
    true: RoomParams,
    d5: DriveSeries,
    d1: DriveSeries,
    c0: float,
    p0: float,
    compliance: float,
    seed: int,
    alpha: float = PROFILE_ALPHA[Profile.BALANCED],
) -> tuple[np.ndarray, SimResult, int]:
    rng = np.random.default_rng(seed)
    aa_true = action_arrays(true)
    aa_model = action_arrays(model)
    n = len(d1)
    src = co2_source_ppm_per_h(d1.n_children, d1.n_adults, true)
    co2, pm = np.empty(n + 1), np.empty(n + 1)
    co2_m, pm_m = np.empty(n), np.empty(n)
    idx = np.empty(n, dtype=np.int64)
    co2[0], pm[0] = c0, p0
    current, requests = 0, 0
    plan: np.ndarray | None = None
    plan_start = 0
    asked: int | None = None
    pending: tuple[int, int] | None = None  # (action, due minute index)
    cfg = CostConfig(alpha=alpha)
    for i in range(n):
        minute = int(d1.t_min[i])
        if (minute - int(d1.t_min[0])) % REPLAN_EVERY_MIN == 0 and i // 5 < len(d5):
            j = i // 5
            res = optimize(
                model,
                d5.slice(j),
                aa_model,
                float(co2[i]),
                float(pm[i]),
                current,
                cfg,
                max_changes=max(MAX_REQUESTS - requests, 0),
                grid=GRID,
            )
            plan, plan_start, asked = res.action_idx, j, None
        assert plan is not None
        k = i // 5 - plan_start
        target = int(plan[min(k, len(plan) - 1)])
        kids_now = d1.n_children[i] > 0 or (i > 0 and d1.n_children[i - 1] > 0)
        if target != current and target != asked and pending is None and requests < MAX_REQUESTS and kids_now:
            requests += 1
            asked = target
            if rng.random() < compliance:
                pending = (target, i + int(rng.integers(1, 4)))
        if pending and i >= pending[1]:
            current, pending = pending[0], None
        idx[i] = current
        co2[i + 1], co2_m[i], pm[i + 1], pm_m[i] = step_true(
            true, aa_true, current, co2[i], pm[i], d1, i, src
        )
    return idx, SimResult(co2=co2, pm=pm, co2_mean=co2_m, pm_mean=pm_m), requests


@dataclass
class Row:
    date: str
    room: str
    policy: str
    pm_dose_ug: float
    co2_min_over_1000: float
    co2_min_over_1500: float
    cold_deg_min: float
    window_changes: int
    requests: int
    max_co2: float
    mean_pm_occupied: float
    outdoor_pm_school_hours: float


def run_day(date: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    day = load_day(date)
    flags = activity_flags(date)
    for room_name, model in ROOMS.items():
        true = hidden_truth(model)
        d5 = drive_for_day(day, model, **flags)
        d1 = d5.resample(1)
        c0, p0 = 520.0, 0.55 * float(d5.pm_out[0])
        aa = action_arrays(true)
        out_pm = float(np.mean(d5.pm_out[d5.children_present]))
        for pol in standard_baselines(compliance=0.7):
            r = run_policy(true, d1, aa, pol, c0, p0, initial=0, seed=stable_seed(date, room_name))
            rows.append(
                Row(
                    date,
                    room_name,
                    pol.name,
                    **_k(r.kpis),
                    requests=r.kpis.window_changes,
                    outdoor_pm_school_hours=out_pm,
                ).__dict__
            )
        runs = [("KHIDKI", 0.7, 0.5), ("KHIDKI_100", 1.0, 0.5)] + [
            (f"KHIDKI_a{a:.1f}", 0.7, a) for a in SWEEP_ALPHAS
        ]
        for name, comp, alpha in runs:
            idx, sim, req = run_khidki(
                model, true, d5, d1, c0, p0, comp, seed=stable_seed(date, room_name, name), alpha=alpha
            )
            k = dose.compute_kpis(d1, sim, aa, idx, 0)
            rows.append(
                Row(date, room_name, name, **_k(k), requests=req, outdoor_pm_school_hours=out_pm).__dict__
            )
    return rows


def _k(k: Any) -> dict[str, Any]:
    return {
        f: getattr(k, f)
        for f in (
            "pm_dose_ug",
            "co2_min_over_1000",
            "co2_min_over_1500",
            "cold_deg_min",
            "window_changes",
            "max_co2",
            "mean_pm_occupied",
        )
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "label": "Simulation on a modelled classroom driven by real outdoor air "
        "(CAMS via Open-Meteo, East Delhi, school days 15 Oct to 19 Dec 2025). "
        "Not a field trial.",
        "rooms": {},
    }
    for room in ROOMS:
        rr = [r for r in rows if r["room"] == room]
        dates = sorted({r["date"] for r in rr})
        by = {(r["date"], r["policy"]): r for r in rr}
        pols: dict[str, Any] = {}
        for pol in POLICIES + SWEEP:
            xs = [by[(d, pol)] for d in dates]
            rel = [by[(d, pol)]["pm_dose_ug"] / by[(d, "ALWAYS_OPEN")]["pm_dose_ug"] * 100 for d in dates]
            pols[pol] = {
                "pm_dose_ug": round(float(np.mean([x["pm_dose_ug"] for x in xs])), 1),
                "pm_pct_of_always_open": round(float(np.mean(rel)), 1),
                "co2_min_over_1500": round(float(np.mean([x["co2_min_over_1500"] for x in xs])), 1),
                "co2_min_over_1000": round(float(np.mean([x["co2_min_over_1000"] for x in xs])), 1),
                "cold_deg_min": round(float(np.mean([x["cold_deg_min"] for x in xs])), 1),
                "requests": round(float(np.mean([x["requests"] for x in xs])), 1),
                "max_co2": round(float(np.mean([x["max_co2"] for x in xs]))),
            }

        def dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
            ka = (a["pm_dose_ug"], a["co2_min_over_1500"])
            kb = (b["pm_dose_ug"], b["co2_min_over_1500"])
            return ka[0] <= kb[0] and ka[1] <= kb[1] and ka != kb

        dom = sum(dominates(by[(d, "KHIDKI")], by[(d, "CO2_ALARM")]) for d in dates)
        dominated = sum(dominates(by[(d, "CO2_ALARM")], by[(d, "KHIDKI")]) for d in dates)
        sweep_dom = {p: sum(dominates(by[(d, p)], by[(d, "CO2_ALARM")]) for d in dates) for p in SWEEP}
        out["rooms"][room] = {
            "days": len(dates),
            "policies": pols,
            "khidki_pareto_dominates_alarm_days": dom,
            "alarm_pareto_dominates_khidki_days": dominated,
            "sweep_pareto_dominates_alarm_days": sweep_dom,
        }
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0, help="limit to the first N days (0 = all)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args(argv)
    days = list_days()[: args.days or None]
    t0 = time.perf_counter()
    print(
        f"Benchmarking {len(days)} days × {len(ROOMS)} rooms × {len(POLICIES) + len(SWEEP)} policies "
        f"on {args.workers} workers…"
    )
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for n, part in enumerate(ex.map(run_day, days), 1):
            rows.extend(part)
            if n % 8 == 0:
                print(f"  {n}/{len(days)} days ({time.perf_counter() - t0:.0f}s)", flush=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "rows.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = summarise(rows)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary["rooms"], indent=1)[:3000])
    print(f"Done in {time.perf_counter() - t0:.0f}s. Next: python bench/report.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
