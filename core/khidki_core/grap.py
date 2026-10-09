"""Indicative GRAP stage from city AQI (CAQM Graded Response Action Plan).

GRAP was revised again on 29 Sep 2026 (some curbs moved to earlier stages). Stage thresholds stay
I: 201 to 300, II: 301 to 400, III: 401 to 450, IV: above 450. School measures change between revisions and
are set by Directorate of Education circulars, not by GRAP stage alone (Stage I never closes schools), so
Khidki does not hard-code which classes go hybrid.

Khidki's stage is *indicative*. The official stage is whatever CAQM has ordered, and the principal can set
it. Khidki only reminds and links; it never enforces or contradicts an official order.
"""

from __future__ import annotations

from dataclasses import dataclass

DOE_CIRCULARS_URL = "https://www.edudel.nic.in/"
GRAP_REVISION = "29 Sep 2026"


@dataclass(frozen=True)
class GrapStage:
    stage: int
    name_en: str
    name_hi: str
    school_reminder_en: str
    school_reminder_hi: str


_CHECK_EN = (
    "Schools follow the latest Directorate of Education circular for this stage. "
    "Check it before changing classes."
)
_CHECK_HI = "इस चरण के लिए शिक्षा निदेशालय का ताज़ा परिपत्र देखें। कक्षाओं में बदलाव उसी के अनुसार करें।"

STAGES: dict[int, GrapStage] = {
    0: GrapStage(0, "No GRAP stage", "कोई GRAP चरण नहीं", "", ""),
    1: GrapStage(1, "Stage I (Poor)", "चरण I (ख़राब)", "", ""),
    2: GrapStage(2, "Stage II (Very poor)", "चरण II (बहुत ख़राब)", _CHECK_EN, _CHECK_HI),
    3: GrapStage(
        3,
        "Stage III (Severe)",
        "चरण III (गंभीर)",
        "At Stage III the DoE has ordered hybrid classes for younger students before. " + _CHECK_EN,
        "चरण III पर शिक्षा निदेशालय पहले छोटी कक्षाओं के लिए हाइब्रिड पढ़ाई का आदेश दे चुका है। " + _CHECK_HI,
    ),
    4: GrapStage(
        4,
        "Stage IV (Severe+)",
        "चरण IV (अति गंभीर)",
        "At Stage IV schools can be ordered to close or go hybrid. " + _CHECK_EN,
        "चरण IV पर स्कूल बंद या हाइब्रिड करने का आदेश हो सकता है। " + _CHECK_HI,
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
