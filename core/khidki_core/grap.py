"""Indicative GRAP stage from city AQI (CAQM Graded Response Action Plan, revised Dec 2024).

Khidki's stage is *indicative*. The official stage is whatever CAQM has ordered, and the principal can set
it. Khidki only reminds and links; it never enforces or contradicts an official order.
"""

from __future__ import annotations

from dataclasses import dataclass

DOE_CIRCULARS_URL = "https://www.edudel.nic.in/"


@dataclass(frozen=True)
class GrapStage:
    stage: int
    name_en: str
    name_hi: str
    school_reminder_en: str
    school_reminder_hi: str


STAGES: dict[int, GrapStage] = {
    0: GrapStage(0, "No GRAP stage", "कोई GRAP चरण नहीं", "", ""),
    1: GrapStage(1, "Stage I (Poor)", "चरण I (ख़राब)", "", ""),
    2: GrapStage(2, "Stage II (Very poor)", "चरण II (बहुत ख़राब)", "", ""),
    3: GrapStage(
        3,
        "Stage III (Severe)",
        "चरण III (गंभीर)",
        "Under revised GRAP, classes up to V move to hybrid mode. Check the latest DoE circular.",
        "संशोधित GRAP के तहत कक्षा V तक हाइब्रिड मोड में। ताज़ा DoE परिपत्र देखें।",
    ),
    4: GrapStage(
        4,
        "Stage IV (Severe+)",
        "चरण IV (अति गंभीर)",
        "Under revised GRAP, classes VI to IX and XI also move to hybrid mode. "
        "Check the latest DoE circular.",
        "संशोधित GRAP के तहत कक्षा VI से IX और XI भी हाइब्रिड मोड में। ताज़ा DoE परिपत्र देखें।",
    ),
}


def indicative_stage(city_aqi: float) -> int:
    if city_aqi > 450:
        return 4
    if city_aqi > 400:
        return 3
    if city_aqi > 300:
        return 2
    if city_aqi > 200:
        return 1
    return 0


def effective_stage(indicative: int, official: int | None) -> int:
    """The official stage always wins when the principal has set one."""
    return official if official is not None else indicative
