"""Window state recovered from a noisy CO₂ curve: no sensor on the window."""

import numpy as np
import pytest

from khidki_core.inference import Verdict, WindowTracker, blend, classify_window, fit_ach, verify_ventilation
from khidki_core.physics import co2_source_ppm_per_h, relax
from khidki_core.schemas import WINDOW_ORDER, RoomParams, Window

ROOM = RoomParams()
FP = dict(ROOM.lam)


def noisy_curve(
    lam: float, c0: float, occupied: bool, rng: np.random.Generator, minutes: float = 4.5, every_s: int = 30
) -> tuple[np.ndarray, np.ndarray, float]:
    src = float(co2_source_ppm_per_h(44, 1, ROOM)) if occupied else 0.0
    t_h = np.arange(0, minutes * 60 + 1, every_s) / 3600
    clean = np.array([float(relax(c0, lam, lam * 450 + src, t)[0]) for t in t_h])
    offset = rng.uniform(-30, 30)
    gain = 1 + rng.uniform(-0.03, 0.03)
    return t_h, clean * gain + offset + rng.normal(0, 10, len(t_h)), src


def test_fit_recovers_lambda_without_noise() -> None:
    src = float(co2_source_ppm_per_h(44, 1, ROOM))
    t_h = np.arange(0, 301, 30) / 3600
    co2 = np.array([float(relax(1600.0, 6.0, 6.0 * 450 + src, t)[0]) for t in t_h])
    assert fit_ach(t_h, co2, 450, src).lam == pytest.approx(6.0, rel=0.03)


def test_window_state_recovered_at_least_90_percent() -> None:
    rng = np.random.default_rng(7)
    correct = total = 0
    for w in WINDOW_ORDER:
        for c0 in (900.0, 1300.0, 1700.0, 2200.0):
            for occupied in (True, False):
                for _ in range(5):
                    t_h, z, src = noisy_curve(FP[w], c0, occupied, rng)
                    guess = classify_window(fit_ach(t_h, z, 450, src).lam, FP)
                    correct += guess.window == w
                    total += 1
    assert correct / total >= 0.9, f"{correct}/{total}"


def test_partial_open_is_detected() -> None:
    """Teacher says both sides are open, but only one side is: λ ≈ 0.45 × λ_open_both."""
    rng = np.random.default_rng(3)
    t_h, z, src = noisy_curve(FP[Window.OPEN_BOTH] * 0.45, 1800.0, True, rng)
    v = verify_ventilation(Window.OPEN_BOTH, fit_ach(t_h, z, 450, src), FP)
    assert v.verdict == Verdict.PARTIAL


def test_full_open_verified_and_nothing_changed_caught() -> None:
    rng = np.random.default_rng(4)
    t_h, z, src = noisy_curve(FP[Window.OPEN_BOTH], 1800.0, True, rng)
    assert verify_ventilation(Window.OPEN_BOTH, fit_ach(t_h, z, 450, src), FP).verdict == Verdict.VERIFIED
    t_h, z, src = noisy_curve(FP[Window.CLOSED], 1800.0, True, rng)
    assert verify_ventilation(Window.OPEN_BOTH, fit_ach(t_h, z, 450, src), FP).verdict == Verdict.NOT_CHANGED


def test_closing_verified() -> None:
    rng = np.random.default_rng(5)
    t_h, z, src = noisy_curve(FP[Window.CLOSED], 900.0, True, rng)
    assert verify_ventilation(Window.CLOSED, fit_ach(t_h, z, 450, src), FP).verdict == Verdict.VERIFIED


def test_tracker_hysteresis() -> None:
    from khidki_core.inference import WindowGuess

    tr = WindowTracker()
    assert tr.update(WindowGuess(Window.OPEN_ONE, 0.55)) == Window.CLOSED
    assert tr.update(WindowGuess(Window.OPEN_ONE, 0.6)) == Window.OPEN_ONE
    assert tr.update(WindowGuess(Window.CLOSED, 0.9)) == Window.CLOSED


def test_blend() -> None:
    assert blend(1000, 1100, 0.6) == pytest.approx(1060)
    assert blend(1000, None, 0.6) == 1000
