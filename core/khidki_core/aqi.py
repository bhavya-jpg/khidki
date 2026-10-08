"""CPCB National AQI, PM2.5 sub-index (2014 methodology, 24-hour breakpoints).

The 2014 table gives Severe as "250+". To interpolate inside that band we take 380 µg/m³ as the top of the
scale (AQI 500) and cap at 500. Documented in docs/physics.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from khidki_core.physics import FloatArray


@dataclass(frozen=True)
class Category:
    key: str
    name_en: str
    name_hi: str
    aqi_lo: int
    aqi_hi: int
    conc_lo: float
    conc_hi: float


PM25_CATEGORIES: tuple[Category, ...] = (
    Category("good", "Good", "अच्छा", 0, 50, 0, 30),
    Category("satisfactory", "Satisfactory", "संतोषजनक", 51, 100, 31, 60),
    Category("moderate", "Moderate", "मध्यम", 101, 200, 61, 90),
    Category("poor", "Poor", "ख़राब", 201, 300, 91, 120),
    Category("very_poor", "Very poor", "बहुत ख़राब", 301, 400, 121, 250),
    Category("severe", "Severe", "गंभीर", 401, 500, 251, 380),
)


def pm25_subindex(conc_ug_m3: float) -> int:
    """PM2.5 sub-index for a 24-hour mean concentration. Values falling between bands (e.g. 30.5) use the
    lower edge of the next band."""
    c = max(0.0, float(conc_ug_m3))
    for cat in PM25_CATEGORIES:
        if c <= cat.conc_hi or cat is PM25_CATEGORIES[-1]:
            c_clamped = min(max(c, cat.conc_lo), cat.conc_hi)
            frac = (c_clamped - cat.conc_lo) / (cat.conc_hi - cat.conc_lo)
            return round(cat.aqi_lo + frac * (cat.aqi_hi - cat.aqi_lo))
    raise AssertionError("unreachable")


def category_for_aqi(aqi: float) -> Category:
    for cat in PM25_CATEGORIES:
        if aqi <= cat.aqi_hi:
            return cat
    return PM25_CATEGORIES[-1]


def rolling_24h_mean(hourly: FloatArray) -> FloatArray:
    """Trailing 24-hour mean of an hourly series (shorter windows at the start)."""
    x = np.asarray(hourly, dtype=np.float64)
    csum = np.concatenate([[0.0], np.cumsum(x)])
    idx = np.arange(1, len(x) + 1)
    lo = np.maximum(0, idx - 24)
    return np.asarray((csum[idx] - csum[lo]) / (idx - lo), dtype=np.float64)
