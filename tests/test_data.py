"""Outdoor data: bias correction, CPCB parsing, cache fallback, replay days."""

import math

import numpy as np
import pytest

from khidki_core.schemas import RoomParams
from khidki_data.bias import bias_ratio, correct
from khidki_data.cache import MemoryCache, fetch_with_cache
from khidki_data.cpcb import haversine_km, nearest_pm25, parse_records
from khidki_data.http import FetchError
from khidki_data.replay import drive_for_day, list_days, load_day


def test_bias_ratio_is_median_of_last_six_and_clipped() -> None:
    obs = [100, 200, 300, 300, 300, 300, 300, 300]
    fc = [100] * 8
    r = bias_ratio(obs, fc)
    assert r.ratio == 3.0 and r.n_pairs == 6 and r.corrected
    assert bias_ratio([1000] * 6, [100] * 6).ratio == 4.0
    assert bias_ratio([10] * 6, [100] * 6).ratio == 0.5


def test_no_observations_means_uncorrected() -> None:
    r = bias_ratio([None, None], [100, 120])
    assert r.ratio == 1.0 and not r.corrected


def test_correction_fades_with_lead_time() -> None:
    out = correct([100, 100, 100, None], 2.0, [0, 12, 120, 1])
    assert out[0] == pytest.approx(200)
    assert out[1] == pytest.approx(100 * (1 + math.exp(-1)))
    assert out[2] == pytest.approx(100, rel=1e-3)
    assert out[3] is None


PAYLOAD = {
    "records": [
        {
            "station": "Anand Vihar, Delhi - DPCC",
            "latitude": "28.647622",
            "longitude": "77.315809",
            "pollutant_id": "PM2.5",
            "avg_value": "312",
            "last_update": "12-11-2025 09:00:00",
        },
        {
            "station": "ITO, Delhi - CPCB",
            "latitude": "28.628624",
            "longitude": "77.241060",
            "pollutant_id": "PM2.5",
            "avg_value": "NA",
            "last_update": "12-11-2025 09:00:00",
        },
        {
            "station": "Anand Vihar, Delhi - DPCC",
            "latitude": "28.647622",
            "longitude": "77.315809",
            "pollutant_id": "NO2",
            "avg_value": "80",
            "last_update": "12-11-2025 09:00:00",
        },
        {"station": "bad", "latitude": "NA", "longitude": "77", "pollutant_id": "PM2.5", "avg_value": "1"},
    ]
}


def test_cpcb_parse_and_nearest() -> None:
    recs = parse_records(PAYLOAD)
    assert len(recs) == 3
    hit = nearest_pm25(recs, 28.6469, 77.3152)
    assert hit is not None
    assert hit[0].station.startswith("Anand Vihar") and hit[0].avg == 312
    assert hit[1] < 1.0


def test_haversine_delhi_distance() -> None:
    assert haversine_km(28.6469, 77.3152, 28.6286, 77.2411) == pytest.approx(7.5, abs=0.5)


def test_cache_serves_last_good_copy_when_fetch_fails() -> None:
    cache = MemoryCache()
    first = fetch_with_cache(cache, "k", lambda: {"pm": 1}, now=1000.0)
    assert not first.stale

    def boom() -> dict[str, int]:
        raise FetchError("down")

    second = fetch_with_cache(cache, "k", boom, now=1600.0)
    assert second.stale and second.value == {"pm": 1}
    assert second.age_min(now=1600.0) == pytest.approx(10.0)
    with pytest.raises(FetchError):
        fetch_with_cache(MemoryCache(), "k", boom)


def test_replay_days_present_and_drive_is_sane() -> None:
    days = list_days()
    assert len(days) >= 40
    day = load_day(days[0])
    drive = drive_for_day(day, RoomParams())
    assert len(drive) == 78
    assert np.all(drive.pm_out >= 0) and np.all(np.isfinite(drive.temp_out))
    assert drive.n_children.max() == 44 and drive.n_children.min() == 0
