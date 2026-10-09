"""State estimation and window inference from the CO₂ curve.

The children's own breath is a tracer gas. Over a short window with known occupancy, CO₂ follows
C(t) = C_ss + (C₀ − C_ss)·e^{−λt} with C_ss = C_out + S/λ. Fitting λ tells us how open the room really is,
with no sensor on the window (the tracer-gas decay idea behind ASTM E741).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from khidki_core.physics import FloatArray
from khidki_core.schemas import WINDOW_ORDER, Window

LAMBDA_SEARCH = np.geomspace(0.05, 25.0, 400)


def blend(predicted: float, measured: float | None, gain: float) -> float:
    """Complementary filter: x̂ = x_pred + K·(z − x_pred). No reading → trust the model."""
    if measured is None or not np.isfinite(measured):
        return predicted
    return predicted + gain * (measured - predicted)


CO2_GAIN = 0.6
PM_GAIN = 0.4


@dataclass(frozen=True)
class AchFit:
    lam: float
    """Implied air changes per hour."""
    rmse: float
    r2: float
    n: int


def fit_ach(
    t_h: FloatArray,
    co2: FloatArray,
    c_out: float,
    source_ppm_h: float,
    lambdas: FloatArray = LAMBDA_SEARCH,
) -> AchFit:
    """Least-squares λ for C(t) = C_ss(λ) + A·e^{−λt}, with A solved in closed form for every candidate λ.

    `source_ppm_h` is the CO₂ source from occupancy (0 for an empty-room decay)."""
    t = np.asarray(t_h, dtype=np.float64) - float(t_h[0])
    z = np.asarray(co2, dtype=np.float64)
    if len(z) < 3:
        raise ValueError("need at least 3 readings to fit an air-change rate")
    lam = lambdas[:, None]
    css = c_out + source_ppm_h / lam  # (L, 1)
    e = np.exp(-lam * t[None, :])  # (L, n)
    amp = np.sum((z[None, :] - css) * e, axis=1, keepdims=True) / np.sum(e * e, axis=1, keepdims=True)
    resid = z[None, :] - (css + amp * e)
    sse = np.sum(resid * resid, axis=1)
    best = int(np.argmin(sse))
    sst = float(np.sum((z - z.mean()) ** 2))
    return AchFit(
        lam=float(lambdas[best]),
        rmse=float(np.sqrt(sse[best] / len(z))),
        r2=1.0 - float(sse[best]) / sst if sst > 0 else 0.0,
        n=len(z),
    )


@dataclass(frozen=True)
class WindowGuess:
    window: Window
    confidence: float


def classify_window(lam: float, fingerprint: dict[Window, float]) -> WindowGuess:
    """Nearest window state in log(λ). Confidence falls as λ sits between two states."""
    states = list(WINDOW_ORDER)
    d = np.array([abs(np.log(max(lam, 1e-3)) - np.log(fingerprint[w])) for w in states])
    order = np.argsort(d)
    nearest, second = int(order[0]), int(order[1])
    confidence = 1.0 - d[nearest] / (d[nearest] + d[second]) if d[nearest] + d[second] > 0 else 1.0
    return WindowGuess(window=states[nearest], confidence=round(float(confidence), 2))


class WindowTracker:
    """Hysteresis over successive guesses: switch state only on a confident guess or two in a row."""

    def __init__(self, initial: Window = Window.CLOSED, confident: float = 0.75) -> None:
        self.state = initial
        self.confidence = 1.0
        self._pending: Window | None = None
        self._confident = confident

    def update(self, guess: WindowGuess) -> Window:
        if guess.window == self.state:
            self._pending = None
            self.confidence = guess.confidence
        elif guess.confidence >= self._confident or self._pending == guess.window:
            self.state, self.confidence, self._pending = guess.window, guess.confidence, None
        else:
            self._pending = guess.window
        return self.state


class Verdict(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    NOT_CHANGED = "not_changed"


@dataclass(frozen=True)
class Verification:
    verdict: Verdict
    implied_lam: float
    expected_lam: float
    inferred: WindowGuess


def verify_ventilation(
    instructed: Window, fit: AchFit, fingerprint: dict[Window, float], previous: Window | None = None
) -> Verification:
    """Did the room's air-change rate move the way the instruction asked?

    More open than before: VERIFIED at ≥ 70% of the expected λ; PARTIAL if clearly above "cracked" but short
    of that (e.g. only one side opened); otherwise NOT_CHANGED.

    Less open than before: VERIFIED once λ is below the boundary between the target state and the next more
    open one. Closed and cracked share a boundary on purpose: just after closing, indoor CO₂ is close to
    outdoor and a sensor's ±3% calibration error is enough to make "closed" look like "cracked". What matters
    is that the room is no longer open.
    """
    order = list(WINDOW_ORDER)
    expected = fingerprint[instructed]
    guess = classify_window(fit.lam, fingerprint)
    lam = fit.lam
    prev = previous if previous is not None else Window.CLOSED
    if order.index(instructed) < order.index(prev):
        upper_of = Window.CRACKED if instructed == Window.CLOSED else instructed
        nxt = order[order.index(upper_of) + 1]
        ok = lam <= float(np.sqrt(fingerprint[upper_of] * fingerprint[nxt]))
        verdict = Verdict.VERIFIED if ok else Verdict.NOT_CHANGED
    elif lam >= 0.7 * expected:
        verdict = Verdict.VERIFIED
    elif lam >= 1.5 * fingerprint[Window.CRACKED]:
        verdict = Verdict.PARTIAL
    else:
        verdict = Verdict.NOT_CHANGED
    return Verification(verdict=verdict, implied_lam=round(lam, 2), expected_lam=expected, inferred=guess)
