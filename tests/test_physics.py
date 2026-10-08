"""The dilemma, in numbers (docs/SPEC.md §7.1), plus the exact-step solver."""

from itertools import pairwise

import numpy as np
import pytest

from khidki_core.physics import co2_source_ppm_per_h, relax, steady_state
from khidki_core.schemas import Purifier, RoomParams, Window

ROOM = RoomParams()
ROOM_P = RoomParams(has_purifier=True)


def test_co2_source_for_44_children_and_a_teacher() -> None:
    assert co2_source_ppm_per_h(44, 1, ROOM) == pytest.approx(3450, rel=0.02)


def test_closed_room_steady_state_is_over_5000_ppm() -> None:
    c, _ = steady_state(ROOM, Window.CLOSED, Purifier.OFF, p_out=250)
    assert 5200 < c < 5500


def test_one_period_closed_from_600_ppm_reaches_about_2300() -> None:
    src = co2_source_ppm_per_h(44, 1, ROOM)
    c_end, _ = relax(600.0, 0.7, 0.7 * 450 + src, 40 / 60)
    assert 2250 < float(c_end) < 2450


def test_open_room_steady_state_is_about_1000_ppm() -> None:
    c, _ = steady_state(ROOM, Window.OPEN_ONE, Purifier.OFF, p_out=250)
    assert 980 < c < 1060


@pytest.mark.parametrize(
    ("room", "window", "purifier", "lo", "hi"),
    [
        (ROOM, Window.CLOSED, Purifier.OFF, 150, 160),
        (ROOM, Window.OPEN_ONE, Purifier.OFF, 238, 246),
        (ROOM_P, Window.CLOSED, Purifier.ON, 50, 58),
    ],
)
def test_pm_steady_states_at_250_outdoor(
    room: RoomParams, window: Window, purifier: Purifier, lo: float, hi: float
) -> None:
    _, p = steady_state(room, window, purifier, p_out=250)
    assert lo < p < hi


def test_exact_step_matches_fine_euler() -> None:
    a, b, x0, dt = 6.2, 1500.0, 40.0, 5 / 60
    x_exact, mean_exact = relax(x0, a, b, dt)
    x, acc, n = x0, 0.0, 200_000
    h = dt / n
    for _ in range(n):
        acc += x * h
        x += (b - a * x) * h
    assert float(x_exact) == pytest.approx(x, rel=1e-4)
    assert float(mean_exact) == pytest.approx(acc / dt, rel=1e-4)


def test_exact_step_handles_a_near_zero() -> None:
    x_end, x_mean = relax(500.0, 0.0, 120.0, 0.5)
    assert float(x_end) == pytest.approx(560.0)
    assert float(x_mean) == pytest.approx(530.0)
    x_end2, _ = relax(500.0, 1e-12, 120.0, 0.5)
    assert float(x_end2) == pytest.approx(560.0)


def test_relax_is_monotone_towards_steady_state() -> None:
    xs = [500.0]
    for _ in range(20):
        xs.append(float(relax(xs[-1], 0.7, 0.7 * 450 + 3450, 5 / 60)[0]))
    assert all(b > a for a, b in pairwise(xs))
    assert xs[-1] < (0.7 * 450 + 3450) / 0.7


def test_relax_is_vectorised() -> None:
    x_end, _ = relax(np.array([400.0, 1000.0, 3000.0]), np.array([0.7, 6.0, 10.0]), 2000.0, 5 / 60)
    assert x_end.shape == (3,)
