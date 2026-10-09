"""Simple model-output statistics: scale the CAMS forecast by how wrong it has been lately.

    r = median(observed / forecast) over the last 6 matched hours, clipped to [0.5, 4]
    F'(h) = F(h) · (1 + (r − 1) · exp(−h / 12))      for lead time h hours

The correction fades with lead time. No observations → r = 1 and the forecast is flagged "uncorrected".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median

RATIO_BOUNDS = (0.5, 4.0)
DECAY_H = 12.0


@dataclass(frozen=True)
class BiasResult:
    ratio: float
    n_pairs: int
    corrected: bool


def bias_ratio(observed: list[float | None], forecast: list[float | None], max_pairs: int = 6) -> BiasResult:
    """`observed` and `forecast` are aligned hourly lists ending at the latest hour."""
    pairs = [
        (o, f)
        for o, f in zip(observed, forecast, strict=False)
        if o is not None and f is not None and f > 1.0 and o >= 0.0
    ]
    pairs = pairs[-max_pairs:]
    if not pairs:
        return BiasResult(ratio=1.0, n_pairs=0, corrected=False)
    r = median(o / f for o, f in pairs)
    return BiasResult(ratio=min(max(r, RATIO_BOUNDS[0]), RATIO_BOUNDS[1]), n_pairs=len(pairs), corrected=True)


def correct(forecast: list[float | None], ratio: float, lead_hours: list[float]) -> list[float | None]:
    return [
        None if f is None else f * (1 + (ratio - 1) * math.exp(-max(h, 0.0) / DECAY_H))
        for f, h in zip(forecast, lead_hours, strict=True)
    ]
