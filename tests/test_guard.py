"""Number-fidelity guard: the LLM may rephrase, never invent."""

import pytest

from khidki_agent.guard import check

TOOLS = [
    {
        "co2_ppm": 1623,
        "outdoor_pm25": 142.4,
        "time": "10:05",
        "duration_min": 4,
        "policy_text": {"S2": {"en": "Outdoor activity moves indoors above 90."}},
    }
]


@pytest.mark.parametrize(
    "answer",
    [
        "CO₂ is 1623 ppm, so open both sides for 4 minutes.",
        "CO₂ is 1,623 ppm right now.",
        "CO₂ is about 1,620 ppm.",
        "CO₂ is around 1,600 ppm.",
        "Outside PM2.5 is 142 µg/m³ (policy S2: above 90).",
        "At 10:05, open the windows.",
        "Class 6B: CO₂ १६२३ ppm.",
    ],
)
def test_supported_numbers_pass(answer: str) -> None:
    assert check(answer, TOOLS).ok, check(answer, TOOLS).unsupported


@pytest.mark.parametrize(
    ("answer", "bad"),
    [
        ("CO₂ is 1,900 ppm.", "1,900"),
        ("Outside PM2.5 is 150 µg/m³.", "150"),
        ("Open the windows at 10:15.", "10:15"),
        ("Children breathe 35% less smog.", "35"),
        ("CO₂ १९०० ppm है।", "1900"),
    ],
)
def test_invented_numbers_fail(answer: str, bad: str) -> None:
    r = check(answer, TOOLS)
    assert not r.ok and bad in r.unsupported


def test_names_with_digits_are_not_claims() -> None:
    assert check("PM2.5 and CO₂ in class 6B under policy S2.", TOOLS).ok


def test_rounding_cannot_hide_a_big_change() -> None:
    assert not check("Outside PM2.5 is 100 µg/m³.", [{"pm": 95}]).ok
