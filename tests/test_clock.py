import pytest

from khidki_core.clock import ClockMode, SimClock, ist_epoch, ist_minute


class FakeTime:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


def test_live_clock_is_real_time() -> None:
    ft = FakeTime()
    c = SimClock(real_time=ft)
    assert c.now() == ft.t and not c.is_simulated and c.speed == 1.0


def test_demo_clock_runs_at_speed_from_anchor() -> None:
    ft = FakeTime()
    c = SimClock(real_time=ft)
    c.start_demo("2025-11-18", "07:00", speed=10)
    assert c.state.mode == ClockMode.DEMO
    assert c.date() == "2025-11-18" and c.minute_of_day() == 420
    ft.t += 60  # one real minute = ten simulated minutes
    assert c.minute_of_day() == 430
    assert c.real_seconds(180) == pytest.approx(18)


def test_speed_change_does_not_jump_time() -> None:
    ft = FakeTime()
    c = SimClock(real_time=ft)
    c.start_demo("2025-11-18", "07:00", speed=10)
    ft.t += 60
    before = c.now()
    c.set_speed(30)
    assert c.now() == pytest.approx(before)
    ft.t += 10
    assert c.now() == pytest.approx(before + 300)


def test_pause() -> None:
    ft = FakeTime()
    c = SimClock(real_time=ft)
    c.start_demo("2025-11-18", "07:00", speed=10)
    c.pause()
    t = c.now()
    ft.t += 100
    assert c.now() == t


def test_ist_helpers_round_trip() -> None:
    e = ist_epoch("2025-11-18", 10 * 60 + 5)
    assert ist_minute(e) == pytest.approx(605)
