import numpy as np
import pytest

from khidki_core.aqi import category_for_aqi, pm25_subindex, rolling_24h_mean
from khidki_core.grap import effective_stage, indicative_stage


@pytest.mark.parametrize(
    ("conc", "aqi"),
    [
        (0, 0),
        (30, 50),
        (31, 51),
        (45, 75),
        (60, 100),
        (90, 200),
        (120, 300),
        (250, 400),
        (380, 500),
        (900, 500),
    ],
)
def test_pm25_subindex_breakpoints(conc: float, aqi: int) -> None:
    assert pm25_subindex(conc) == aqi


def test_pm25_150_is_very_poor_about_323() -> None:
    assert pm25_subindex(150) == 323
    assert category_for_aqi(323).key == "very_poor"


def test_values_between_bands_use_next_band_floor() -> None:
    assert pm25_subindex(30.5) == 51


@pytest.mark.parametrize(
    ("aqi", "stage"),
    [(150, 0), (200, 0), (201, 1), (300, 1), (301, 2), (400, 2), (401, 3), (450, 3), (451, 4)],
)
def test_indicative_grap_stage(aqi: int, stage: int) -> None:
    assert indicative_stage(aqi) == stage


def test_official_stage_always_wins() -> None:
    assert effective_stage(2, 4) == 4
    assert effective_stage(4, 1) == 1
    assert effective_stage(3, None) == 3


def test_rolling_mean() -> None:
    x = np.arange(48, dtype=float)
    r = rolling_24h_mean(x)
    assert r[0] == 0
    assert r[23] == pytest.approx(np.mean(x[:24]))
    assert r[47] == pytest.approx(np.mean(x[24:48]))


def test_school_reminders_defer_to_doe_and_name_no_class_lists() -> None:
    from khidki_core.grap import STAGES

    for st in STAGES.values():
        if st.school_reminder_en:
            assert "Directorate of Education" in st.school_reminder_en
            assert "classes VI" not in st.school_reminder_en and "up to V" not in st.school_reminder_en
