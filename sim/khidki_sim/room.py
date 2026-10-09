"""The true classroom, with hidden parameters that differ from Khidki's defaults (so the fingerprint has
something to learn), and a sensor with a fixed calibration error plus noise."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from khidki_core.physics import co2_source_ppm_per_h, relax
from khidki_core.schemas import Purifier, RoomParams, Window


def hidden_truth(base: RoomParams) -> RoomParams:
    """The room as it really is: leakier when shut, a little less airy when open, more deposition."""
    return base.model_copy(
        update={
            "lam": {Window.CLOSED: 0.9, Window.CRACKED: 2.8, Window.OPEN_ONE: 5.2, Window.OPEN_BOTH: 8.8},
            "pen": {Window.CLOSED: 0.75, Window.CRACKED: 0.93, Window.OPEN_ONE: 1.0, Window.OPEN_BOTH: 1.0},
            "deposition_per_h": 0.25,
        }
    )


@dataclass
class Sensor:
    """CO₂ accuracy ±(30 ppm + 3%), PM2.5 ±(5 µg/m³ + 10%): modelled as a fixed per-device calibration error
    plus small random noise per reading."""

    rng: np.random.Generator
    co2_offset: float = 0.0
    co2_gain: float = 1.0
    pm_offset: float = 0.0
    pm_gain: float = 1.0

    @classmethod
    def random(cls, rng: np.random.Generator) -> Sensor:
        return cls(
            rng=rng,
            co2_offset=float(rng.uniform(-30, 30)),
            co2_gain=float(1 + rng.uniform(-0.03, 0.03)),
            pm_offset=float(rng.uniform(-5, 5)),
            pm_gain=float(1 + rng.uniform(-0.1, 0.1)),
        )

    def read(self, co2: float, pm: float) -> tuple[float, float]:
        c = co2 * self.co2_gain + self.co2_offset + float(self.rng.normal(0, 8))
        p = pm * self.pm_gain + self.pm_offset + float(self.rng.normal(0, 2))
        return round(max(c, 350.0)), round(max(p, 0.0), 1)


@dataclass
class TrueRoom:
    room_id: str
    params: RoomParams
    sensor: Sensor
    co2: float = 550.0
    pm: float = 120.0
    window: Window = Window.CLOSED
    purifier: Purifier = Purifier.OFF
    lam_override: float | None = None
    """Set when the window is physically half-done (e.g. only one side opened)."""
    history: list[tuple[float, Window, float | None]] = field(default_factory=list)

    def set(self, window: Window, purifier: Purifier, at: float, lam_override: float | None = None) -> None:
        self.window, self.purifier, self.lam_override = window, purifier, lam_override
        self.history.append((at, window, lam_override))

    @property
    def lam(self) -> float:
        return self.lam_override if self.lam_override is not None else self.params.lam[self.window]

    def step(self, dt_s: float, pm_out: float, co2_out: float, kids: float, adults: float) -> None:
        p = self.params
        dt_h = dt_s / 3600.0
        lam = self.lam
        src = float(co2_source_ppm_per_h(kids, adults, p))
        self.co2 = float(relax(self.co2, lam, lam * co2_out + src, dt_h)[0])
        q = p.purifier_cadr_m3_h * p.purifier_effectiveness if self.purifier == Purifier.ON else 0.0
        a = lam + p.deposition_per_h + q / p.volume_m3
        self.pm = float(relax(self.pm, a, p.pen[self.window] * lam * pm_out, dt_h)[0])
