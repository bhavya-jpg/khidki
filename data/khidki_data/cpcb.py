"""CPCB real-time AQI via data.gov.in (resource 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69), GODL-India.

Used as a nowcast to bias-correct the coarse CAMS forecast. The parser is tolerant about field names because
the payload format is checked against a real response once a personal API key is available (see
docs/LEARNINGS.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from khidki_data.http import get_json

RESOURCE_URL = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"


@dataclass(frozen=True)
class StationReading:
    station: str
    lat: float
    lon: float
    pollutant: str
    avg: float | None
    last_update: str


def _num(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def parse_records(payload: dict[str, Any]) -> list[StationReading]:
    out: list[StationReading] = []
    for r in payload.get("records", []):
        lat, lon = _num(r.get("latitude")), _num(r.get("longitude"))
        if lat is None or lon is None:
            continue
        out.append(
            StationReading(
                station=str(r.get("station", "")),
                lat=lat,
                lon=lon,
                pollutant=str(r.get("pollutant_id", "")).upper().replace(".", ""),
                avg=_num(r.get("avg_value", r.get("pollutant_avg"))),
                last_update=str(r.get("last_update", "")),
            )
        )
    return out


def fetch_city(api_key: str, city: str = "Delhi", timeout_s: float = 8.0) -> list[StationReading]:
    payload = get_json(
        RESOURCE_URL,
        {"api-key": api_key, "format": "json", "limit": 1000, "filters[city]": city},
        timeout_s=timeout_s,
    )
    return parse_records(payload)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def nearest_pm25(
    readings: list[StationReading], lat: float, lon: float
) -> tuple[StationReading, float] | None:
    """Nearest station with a PM2.5 value, and its distance in km."""
    pm = [r for r in readings if r.pollutant == "PM25" and r.avg is not None]
    if not pm:
        return None
    best = min(pm, key=lambda r: haversine_km(lat, lon, r.lat, r.lon))
    return best, haversine_km(lat, lon, best.lat, best.lon)
