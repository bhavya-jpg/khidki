"""Room fingerprint recovers known parameters from a simulated, noisy day."""

import numpy as np
import pytest

from khidki_core.calibration import Telemetry, apply_fingerprint, fit_fingerprint
from khidki_core.physics import co2_source_ppm_per_h, relax
from khidki_core.schemas import RoomParams, Window
from khidki_core.timetable import occupancy

PRIOR = RoomParams()
TRUE = RoomParams(
    lam={Window.CLOSED: 0.9, Window.CRACKED: 3.0, Window.OPEN_ONE: 5.0, Window.OPEN_BOTH: 8.5},
    pen={Window.CLOSED: 0.7, Window.CRACKED: 0.95, Window.OPEN_ONE: 1.0, Window.OPEN_BOTH: 1.0},
    deposition_per_h=0.3,
)


def schedule(minute: int) -> Window:
    """A day that visits every window state, including empty-room decays."""
    blocks = [
        (450, Window.CLOSED),
        (470, Window.OPEN_BOTH),
        (480, Window.CLOSED),
        (525, Window.CRACKED),
        (560, Window.CLOSED),
        (590, Window.OPEN_ONE),
        (610, Window.OPEN_BOTH),
        (640, Window.CLOSED),
        (700, Window.OPEN_ONE),
        (730, Window.CRACKED),
        (780, Window.OPEN_BOTH),
        (800, Window.CLOSED),
    ]
    state = Window.CLOSED
    for start, w in blocks:
        if minute >= start:
            state = w
    return state


def simulate_day(truth: RoomParams, seed: int = 0) -> Telemetry:
    rng = np.random.default_rng(seed)
    t_min = np.arange(7 * 60, 14 * 60, 0.5)
    kids, adults = occupancy(t_min.astype(np.int64), truth.students, truth.adults)
    h = (t_min - 420) / 60
    pm_out = 220 - 20 * h + 25 * np.sin(h * 1.7)
    windows = tuple(schedule(int(m)) for m in t_min)
    c = np.empty(len(t_min))
    p = np.empty(len(t_min))
    c[0], p[0] = 600.0, 150.0
    dt = 0.5 / 60
    for i in range(1, len(t_min)):
        j = i - 1
        lam = truth.lam[windows[j]]
        src = float(co2_source_ppm_per_h(kids[j], adults[j], truth))
        c[i] = float(relax(c[j], lam, lam * 450 + src, dt)[0])
        a = lam + truth.deposition_per_h
        p[i] = float(relax(p[j], a, truth.pen[windows[j]] * lam * pm_out[j], dt)[0])
    return Telemetry(
        t_h=t_min / 60,
        co2=c + rng.normal(0, 10, len(c)),
        pm=p * (1 + rng.normal(0, 0.05, len(p))) + rng.normal(0, 2, len(p)),
        pm_out=pm_out,
        co2_out=np.full(len(c), 450.0),
        n_children=kids,
        n_adults=adults,
        window=windows,
        purifier_on=np.zeros(len(c), dtype=bool),
    )


def test_recovers_room_parameters() -> None:
    fp = fit_fingerprint(simulate_day(TRUE), PRIOR)
    assert fp.accepted, fp.notes
    for w, lam in TRUE.lam.items():
        assert fp.lam[w] == pytest.approx(lam, rel=0.10), w
    assert fp.pen_closed == pytest.approx(0.7, rel=0.20)
    assert fp.deposition_per_h == pytest.approx(0.3, rel=0.20)
    assert fp.co2_r2 > 0.95


def test_rejects_non_physical_fits() -> None:
    tel = simulate_day(TRUE)
    garbage = Telemetry(**{**tel.__dict__, "pm": np.random.default_rng(1).uniform(0, 400, len(tel.pm))})
    fp = fit_fingerprint(garbage, PRIOR)
    assert not fp.accepted
    assert apply_fingerprint(PRIOR, fp) is PRIOR


def test_apply_updates_twin() -> None:
    fp = fit_fingerprint(simulate_day(TRUE), PRIOR)
    room = apply_fingerprint(PRIOR, fp)
    assert room.lam[Window.CLOSED] == pytest.approx(0.9, rel=0.1)
    assert room.pen[Window.CLOSED] == fp.pen_closed
