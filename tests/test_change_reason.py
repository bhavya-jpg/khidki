"""The reason shown for a change, judged from the change itself (engine.change_reason)."""

from khidki_core.schemas import Action, Purifier, ReasonCode, Window
from khidki_services.engine import change_reason


def a(window: Window, purifier: Purifier = Purifier.OFF) -> Action:
    return Action(window=window, purifier=purifier)


def test_opening_with_children_is_about_co2() -> None:
    assert change_reason(a(Window.CLOSED), a(Window.OPEN_ONE), True) == ReasonCode.CO2_RISING_FAST
    assert change_reason(a(Window.OPEN_ONE), a(Window.OPEN_BOTH), True) == ReasonCode.CO2_RISING_FAST


def test_opening_an_empty_room_is_a_purge() -> None:
    assert change_reason(a(Window.CLOSED), a(Window.OPEN_BOTH), False) == ReasonCode.RECESS_PURGE


def test_closing_keeps_the_smog_out_or_lets_the_purifier_work() -> None:
    assert change_reason(a(Window.OPEN_BOTH), a(Window.OPEN_ONE), True) == ReasonCode.AIR_REFRESHED
    assert change_reason(a(Window.OPEN_ONE), a(Window.CLOSED), True) == ReasonCode.AIR_REFRESHED
    closed_purifying = a(Window.CLOSED, Purifier.ON)
    assert change_reason(a(Window.OPEN_ONE), closed_purifying, True) == ReasonCode.PURIFIER_DURING_CLOSED


def test_a_purifier_only_change_is_about_the_purifier() -> None:
    assert (
        change_reason(a(Window.CLOSED), a(Window.CLOSED, Purifier.ON), True)
        == ReasonCode.PURIFIER_DURING_CLOSED
    )


def test_it_never_answers_keep_steady() -> None:
    for before in Window:
        for after in Window:
            for kids in (True, False):
                assert change_reason(a(before), a(after), kids) != ReasonCode.KEEP_STEADY
