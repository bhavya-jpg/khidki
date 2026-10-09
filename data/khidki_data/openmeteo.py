"""Open-Meteo: CAMS air-quality forecasts and history, and weather. Keyless for non-commercial use.

Attribution is required wherever the data is shown (footer and /how).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from khidki_data.http import get_json

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Asia/Kolkata"
AQ_VARS = ("pm2_5", "pm10", "us_aqi", "carbon_dioxide")
WEATHER_VARS = ("temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation")

ATTRIBUTION = (
    "Air quality: Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo.com, CC BY 4.0. "
    "Weather: Open-Meteo.com, CC BY 4.0. Contains modified Copernicus Atmosphere Monitoring Service information."
)


@dataclass
class Hourly:
    """Hourly series keyed by variable name. `time` is local ISO time (Asia/Kolkata), e.g. 2025-11-12T07:00."""

    time: list[str]
    values: dict[str, list[float | None]] = field(default_factory=dict)
    source: str = ""

    def merge(self, other: Hourly) -> Hourly:
        """Join two series on time (inner join)."""
        idx = {t: i for i, t in enumerate(other.time)}
        keep = [i for i, t in enumerate(self.time) if t in idx]
        merged = {k: [v[i] for i in keep] for k, v in self.values.items()}
        for k, v in other.values.items():
            merged[k] = [v[idx[self.time[i]]] for i in keep]
        return Hourly(
            time=[self.time[i] for i in keep], values=merged, source=f"{self.source}+{other.source}"
        )

    def day(self, date: str) -> Hourly:
        keep = [i for i, t in enumerate(self.time) if t.startswith(date)]
        return Hourly(
            time=[self.time[i] for i in keep],
            values={k: [v[i] for i in keep] for k, v in self.values.items()},
            source=self.source,
        )

    def to_json(self) -> dict[str, Any]:
        return {"time": self.time, "values": self.values, "source": self.source}

    @staticmethod
    def from_json(d: dict[str, Any]) -> Hourly:
        return Hourly(
            time=list(d["time"]),
            values={k: list(v) for k, v in d["values"].items()},
            source=d.get("source", ""),
        )


def _parse(payload: dict[str, Any], variables: tuple[str, ...], source: str) -> Hourly:
    hourly = payload.get("hourly") or {}
    return Hourly(
        time=list(hourly.get("time", [])),
        values={v: list(hourly.get(v, [])) for v in variables},
        source=source,
    )


def air_quality(
    lat: float,
    lon: float,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    forecast_days: int = 2,
    past_days: int = 1,
    timeout_s: float = 8.0,
) -> Hourly:
    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(AQ_VARS),
        "timezone": TIMEZONE,
    }
    if start_date:
        params.update(start_date=start_date, end_date=end_date or start_date)
    else:
        params.update(forecast_days=forecast_days, past_days=past_days)
    return _parse(get_json(AQ_URL, params, timeout_s=timeout_s), AQ_VARS, "cams")


def weather(
    lat: float,
    lon: float,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    forecast_days: int = 2,
    past_days: int = 1,
    timeout_s: float = 8.0,
) -> Hourly:
    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(WEATHER_VARS),
        "timezone": TIMEZONE,
    }
    if start_date:
        params.update(start_date=start_date, end_date=end_date or start_date)
        url = WEATHER_ARCHIVE_URL
    else:
        params.update(forecast_days=forecast_days, past_days=past_days)
        url = WEATHER_FORECAST_URL
    return _parse(get_json(url, params, timeout_s=timeout_s), WEATHER_VARS, "openmeteo-weather")
