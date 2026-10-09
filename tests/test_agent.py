"""Ask Khidki: deterministic tools, template fallback, guard on LLM answers."""

from khidki_agent.answer import ask, intent_of, time_in
from khidki_agent.tools import Tools
from khidki_core.clock import SimClock
from khidki_core.optimizer import Grid
from khidki_services.engine import Engine
from khidki_services.outdoor import ReplayOutdoor
from khidki_services.store import MemoryStore


def engine_at(hhmm: str = "10:00") -> Engine:
    t = [1_000_000.0]
    clock = SimClock(real_time=lambda: t[0])
    clock.start_demo("2025-11-18", hhmm, 1.0)
    e = Engine(MemoryStore(), clock, ReplayOutdoor("2025-11-18"), grid=Grid(co2_step=50, pm_step=5))
    e.seed()
    e.tick()
    return e


def test_intents_and_times() -> None:
    assert intent_of("Kya main 11:20 pe PT ke liye bachchon ko bahar le jaun?") == "activity"
    assert intent_of("खिड़की कब खोलूँ?") == "window"
    assert intent_of("Why should I open now?") == "why"
    assert intent_of("Bahar hawa kaisi hai?") == "outdoor"
    assert intent_of("Kya bachche bahar khel sakte hain?") == "activity"
    assert time_in("Kya 11:20 pe PT?") == "11:20"
    assert time_in("2 baje bahar?") == "14:00"


def test_pe_question_is_answered_with_policy_and_numbers() -> None:
    tools = Tools(engine_at())
    a = ask(tools, "6B", "Kya main 11:20 pe PT ke liye bachchon ko bahar le jaun?", "hi")
    assert a.source == "template" and a.numbers_verified
    assert "S2" in a.answer and "11:20" in a.answer
    assert "check_activity" in a.tools_used


def test_llm_answer_with_invented_number_is_replaced() -> None:
    tools = Tools(engine_at())

    def lying_llm(q, lang, calls):  # type: ignore[no-untyped-def]
        return "Take them out, PM2.5 is only 42 µg/m³."

    a = ask(tools, "6B", "Should we do PE outside at 11:20?", "en", llm=lying_llm)
    assert a.source == "template" and "42" in (a.note or "")


def test_llm_answer_that_copies_numbers_is_kept() -> None:
    tools = Tools(engine_at())

    def honest_llm(q, lang, calls):  # type: ignore[no-untyped-def]
        now = calls[0][1]
        return f"CO₂ in the room is {now['co2_ppm']} ppm."

    a = ask(tools, "6B", "Should I open the window?", "en", llm=honest_llm)
    assert a.source == "llm"


def test_bedrock_failure_falls_back_to_template() -> None:
    tools = Tools(engine_at())

    def down(q, lang, calls):  # type: ignore[no-untyped-def]
        raise TimeoutError("Bedrock took longer than 8 s")

    a = ask(tools, "6B", "Should I open the window?", "en", llm=down)
    assert a.source == "template" and "offline" in (a.note or "")
