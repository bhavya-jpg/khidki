"""Outdoor air for a school: the forecast the planner uses, and the "now" observation used to bias-correct it.

- ReplayOutdoor: a real 2025 day (CAMS) for demos and tests. Scenario events (e.g. a smoke plume) change the
  *true* outdoor air but not the forecast, the way a forecast miss would. The observation stands in for a
  CPCB station and is flagged simulated.
- LiveOutdoor: Open-Meteo forecast now, with CPCB data.gov.in observations when a key is configured.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from khidki_core.clock import ist_minute
from khidki_data import cpcb, openmeteo
from khidki_data.cache import Cache, MemoryCache, fetch_with_cache
from khidki_data.replay import DEMO_LAT, DEMO_LON, load_day


@dataclass(frozen=True)
class OutdoorDay:
    date: str
    hour_min: np.ndarray
    pm25: np.ndarray
    temp: np.ndarray
    co2: np.ndarray
    source: str
    simulated: bool
    stale_min: float = 0.0


@dataclass(frozen=True)
class OutdoorEvent:
    start_min: float
    end_min: float
    factor: float


class OutdoorProvider(Protocol):
    def forecast(self, date: str) -> OutdoorDay: ...

    def observe(self, epoch_s: float) -> float | None:
        """Outdoor PM2.5 measured right now near the school, if available."""
        ...


def _value_at(day: OutdoorDay, minute: float) -> float:
    return float(np.interp(minute, day.hour_min, day.pm25))


@dataclass
class ReplayOutdoor:
    date: str
    events: list[OutdoorEvent] = field(default_factory=list)

    def forecast(self, date: str) -> OutdoorDay:
        d = load_day(self.date)
        return OutdoorDay(
            date=date,
            hour_min=d.hour_min,
            pm25=d.series("pm2_5"),
            temp=d.series("temperature_2m"),
            co2=d.series("carbon_dioxide"),
            source=f"CAMS replay of {self.date} (real outdoor air, uncorrected model values)",
            simulated=True,
        )

    def factor_at(self, minute: float) -> float:
        f = 1.0
        for e in self.events:
            if e.start_min <= minute < e.end_min:
                f *= e.factor
        return f

    def true_pm(self, epoch_s: float) -> float:
        m = ist_minute(epoch_s)
        return _value_at(self.forecast(self.date), m) * self.factor_at(m)

    def true_temp(self, epoch_s: float) -> float:
        day = self.forecast(self.date)
        return float(np.interp(ist_minute(epoch_s), day.hour_min, day.temp))

    def observe(self, epoch_s: float) -> float | None:
        return self.true_pm(epoch_s)


@dataclass
class LiveOutdoor:
    lat: float = DEMO_LAT
    lon: float = DEMO_LON
    datagov_key: str | None = None
    cache: Cache = field(default_factory=MemoryCache)

    def forecast(self, date: str) -> OutdoorDay:
        def get() -> dict[str, object]:
            aq = openmeteo.air_quality(self.lat, self.lon)
            wx = openmeteo.weather(self.lat, self.lon)
            return aq.merge(wx).day(date).to_json()

        got = fetch_with_cache(self.cache, f"openmeteo-{date}", get)
        h = openmeteo.Hourly.from_json(got.value)

        def arr(name: str) -> np.ndarray:
            return np.array([np.nan if v is None else v for v in h.values[name]], dtype=np.float64)

        return OutdoorDay(
            date=date,
            hour_min=np.array([int(t[11:13]) * 60 for t in h.time], dtype=np.float64),
            pm25=arr("pm2_5"),
            temp=arr("temperature_2m"),
            co2=arr("carbon_dioxide"),
            source="CAMS forecast via Open-Meteo",
            simulated=False,
            stale_min=got.age_min() if got.stale else 0.0,
        )

    def observe(self, epoch_s: float) -> float | None:
        if not self.datagov_key:
            return None
        key = self.datagov_key

        def get() -> list[dict[str, object]]:
            return [r.__dict__ for r in cpcb.fetch_city(key)]

        try:
            got = fetch_with_cache(self.cache, "cpcb-delhi", get, now=time.time())
        except Exception:
            return None
        readings = [cpcb.StationReading(**r) for r in got.value]  # type: ignore[arg-type]
        hit = cpcb.nearest_pm25(readings, self.lat, self.lon)
        return hit[0].avg if hit else None
