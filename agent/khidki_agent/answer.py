"""Answer a teacher's question: call the tools, then let the LLM phrase it (guarded) or use the template.

Routing to tools is deterministic and the template answer is always built first, so there's always a
correct answer even with no LLM at all.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from khidki_agent import guard
from khidki_agent.tools import Tools

TIME_Q = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")
BAJE_Q = re.compile(r"\b([1-9]|1[0-2])\s*(?:baje|बजे)")

# Most specific first: "PT ke liye bahar?" is about PE; "bahar hawa kaisi hai?" is about the air.
INTENTS: list[tuple[str, tuple[str, ...]]] = [
    (
        "activity",
        ("pe", "pt", "games", "sports", "khel", "खेल", "assembly", "prarthana", "प्रार्थना", "ground", "मैदान"),
    ),
    ("outdoor", ("aqi", "smog", "pollution", "forecast", "hawa", "हवा", "pradushan", "प्रदूषण")),
    ("activity", ("bahar", "बाहर", "outside")),
    ("why", ("why", "kyon", "kyun", "क्यों", "reason", "वजह")),
    (
        "window",
        ("window", "khidki", "खिड़की", "kholu", "kholun", "खोलूँ", "band", "बंद", "open", "close", "purifier"),
    ),
]


@dataclass
class Answer:
    answer: str
    lang: str
    source: str  # "llm" | "template"
    numbers_verified: bool
    tools_used: list[str] = field(default_factory=list)
    tool_outputs: list[dict[str, Any]] = field(default_factory=list)
    note: str | None = None


def intent_of(q: str) -> str:
    ql = q.lower()
    for name, words in INTENTS:
        if any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", ql) for w in words):
            return name
    return "window"


def time_in(q: str) -> str | None:
    m = TIME_Q.search(q)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    m = BAJE_Q.search(q)
    if m:
        h = int(m.group(1))
        return f"{h + 12 if h < 7 else h:02d}:00"
    return None


def gather(tools: Tools, room_id: str, question: str) -> tuple[str, list[tuple[str, dict[str, Any]]]]:
    intent = intent_of(question)
    calls: list[tuple[str, dict[str, Any]]] = [("get_room_now", tools.get_room_now(room_id))]
    if intent == "activity":
        calls.append(("check_activity", tools.check_activity(room_id, time_in(question))))
    elif intent == "outdoor":
        calls.append(("get_outdoor_forecast", tools.get_outdoor_forecast(3)))
    elif intent == "why":
        now = calls[0][1]
        code = (now.get("current_instruction") or now.get("next_change") or {}).get(
            "reason_code", "KEEP_STEADY"
        )
        calls.append(("explain_reason_code", tools.explain_reason_code(code)))
    return intent, calls


def template(intent: str, calls: list[tuple[str, dict[str, Any]]], lang: str) -> str:
    now = calls[0][1]
    hi = lang == "hi"
    if intent == "activity":
        a = calls[1][1]
        pol = next(iter(a["policy_text"].items()), None)
        if not a["allowed_outside"] and pol:
            pid, text = pol
            if hi:
                return (
                    f"नहीं, {a['start']} से {a['end']} तक बच्चों को अंदर ही रखिए। उस समय बाहर PM2.5 का अनुमान "
                    f"{a['outdoor_pm25_max']} µg/m³ तक है। नीति {pid}: {text['hi']} बाहर हर बच्चा लगभग "
                    f"{a['dose_outside_ug']} µg PM2.5 साँस में लेता, अंदर लगभग {a['dose_inside_ug']} µg।"
                )
            return (
                f"No, keep the class indoors from {a['start']} to {a['end']}. "
                f"Outdoor PM2.5 is forecast to reach {a['outdoor_pm25_max']} µg/m³. "
                f"Policy {pid}: {text['en']} Outside, each child would breathe "
                f"about {a['dose_outside_ug']} µg of PM2.5; inside, about {a['dose_inside_ug']} µg."
            )
        if hi:
            return (
                f"हाँ, {a['start']} से {a['end']} तक बाहर जा सकते हैं। बाहर PM2.5 का अनुमान अधिकतम "
                f"{a['outdoor_pm25_max']} µg/m³ है, जो स्कूल नीति की सीमा के अंदर है।"
            )
        return (
            f"Yes, the class can go out from {a['start']} to {a['end']}. "
            f"Outdoor PM2.5 is forecast to peak at {a['outdoor_pm25_max']} µg/m³, "
            "within the school's policy limits."
        )
    if intent == "outdoor":
        f = calls[1][1]
        vals = [r["pm25"] for r in f["hourly"]] or [now["outdoor_pm25"]]
        if hi:
            return (
                f"अभी बाहर AQI {now['outdoor_aqi']} ({now['aqi_category_hi']}) है। अगले कुछ घंटों में PM2.5 "
                f"{min(vals)} से {max(vals)} µg/m³ के बीच रहने का अनुमान है।"
            )
        return (
            f"Outside, the AQI is {now['outdoor_aqi']} ({now['aqi_category_en']}). PM2.5 is forecast between "
            f"{min(vals)} and {max(vals)} µg/m³ over the next few hours."
        )
    if intent == "why":
        r = calls[1][1]
        return r["hi"] if hi else r["en"]
    # window
    co2 = now["co2_ppm"]
    if "current_instruction" in now:
        ci = now["current_instruction"]
        if hi:
            return f"अभी: {ci['hi']}, {ci['duration_min']} मिनट के लिए। कमरे में CO₂ {co2} ppm है।"
        return f"Now: {ci['en']}, for {ci['duration_min']} minutes. CO₂ in the room is {co2} ppm."
    nxt = now.get("next_change")
    if hi:
        tail = f" अगला बदलाव {nxt['time']} पर: {nxt['hi']}।" if nxt else ""
        return f"अभी कुछ नहीं करना है। कमरे में CO₂ {co2} ppm है।{tail}"
    tail = f" Next change at {nxt['time']}: {nxt['en']}." if nxt else ""
    return f"Nothing to do right now. CO₂ in the room is {co2} ppm.{tail}"


LLM = Callable[[str, str, list[tuple[str, dict[str, Any]]]], str]
"""(question, lang, tool calls) -> answer text. Must not add facts beyond the tool outputs."""


def ask(tools: Tools, room_id: str, question: str, lang: str = "hi", llm: LLM | None = None) -> Answer:
    intent, calls = gather(tools, room_id, question)
    base = template(intent, calls, lang)
    outputs = [c[1] for c in calls]
    names = [c[0] for c in calls]
    if llm is None:
        return Answer(base, lang, "template", True, names, outputs, note="verified template")
    try:
        text = llm(question, lang, calls)
    except Exception as exc:  # Bedrock down, throttled or slow: the product must not depend on it
        return Answer(
            base, lang, "template", True, names, outputs, note=f"assistant offline ({type(exc).__name__})"
        )
    g = guard.check(text, outputs)
    if not g.ok:
        return Answer(
            base,
            lang,
            "template",
            True,
            names,
            outputs,
            note=f"assistant answer replaced: unsupported numbers {', '.join(g.unsupported)}",
        )
    return Answer(text, lang, "llm", True, names, outputs)
