"""Fixed bilingual copy for instructions and reasons. The UI and the agent use these; the LLM never invents
instruction text. Hindi is written, not machine-translated word by word (see docs/LEARNINGS.md for phrases
still to be reviewed by a native speaker)."""

from __future__ import annotations

from khidki_core.schemas import Action, Purifier, ReasonCode, Window

ACTION_TEXT: dict[tuple[Window, Purifier], tuple[str, str]] = {
    (Window.CLOSED, Purifier.OFF): ("Close the windows", "खिड़कियाँ बंद कीजिए"),
    (Window.CRACKED, Purifier.OFF): ("Open one window a little", "एक खिड़की थोड़ी खोलिए"),
    (Window.OPEN_ONE, Purifier.OFF): ("Open the road-side windows", "सड़क की तरफ़ की खिड़कियाँ खोलिए"),
    (Window.OPEN_BOTH, Purifier.OFF): ("Open both sides", "दोनों तरफ़ की खिड़कियाँ खोलिए"),
    (Window.CLOSED, Purifier.ON): ("Close the windows, purifier on", "खिड़कियाँ बंद, प्यूरीफ़ायर चालू कीजिए"),
    (Window.CRACKED, Purifier.ON): (
        "One window a little open, purifier on",
        "एक खिड़की थोड़ी खुली, प्यूरीफ़ायर चालू",
    ),
    (Window.OPEN_ONE, Purifier.ON): ("Road side open, purifier on", "सड़क की तरफ़ खिड़कियाँ खोलिए, प्यूरीफ़ायर चालू"),
    (Window.OPEN_BOTH, Purifier.ON): ("Open both sides, purifier on", "दोनों तरफ़ खोलिए, प्यूरीफ़ायर चालू"),
}

# What the teacher taps, named for what just happened.
DONE_BUTTON: dict[str, tuple[str, str]] = {
    "open": ("I've opened them", "खोल दीं"),
    "close": ("I've closed them", "बंद कर दीं"),
    "purifier": ("Turned it on", "चालू कर दिया"),
}
CANT_BUTTON = ("Can't right now", "अभी नहीं हो सकता")
CANT_REASONS: dict[str, tuple[str, str]] = {
    "cold": ("Too cold", "ठंड"),
    "noise": ("Too noisy", "शोर"),
    "rain": ("Raining", "बारिश"),
    "exam": ("Exam on", "परीक्षा"),
}

REASON_TEXT: dict[ReasonCode, tuple[str, str]] = {
    ReasonCode.CO2_RISING_FAST: (
        "CO₂ is rising fast. Fresh air now keeps the class alert.",
        "CO₂ तेज़ी से बढ़ रहा है। अभी ताज़ी हवा से बच्चे चुस्त रहेंगे।",
    ),
    ReasonCode.OUTDOOR_PM_LOW_WINDOW: (
        "Outside air is at its cleanest for a while. A good time to air the room.",
        "बाहर की हवा अभी कुछ देर के लिए सबसे साफ़ है। कमरे में हवा बदलने का अच्छा समय।",
    ),
    ReasonCode.RECESS_PURGE: (
        "The room is empty for recess. Flush out the stale air now.",
        "रिसेस में कमरा ख़ाली है। अभी पूरी हवा बदल दीजिए।",
    ),
    ReasonCode.OUTDOOR_PM_SPIKE_CLOSE: (
        "Outside smog is about to get worse. Close up for now.",
        "बाहर स्मॉग बढ़ने वाला है। अभी के लिए बंद कर दीजिए।",
    ),
    ReasonCode.PURIFIER_DURING_CLOSED: (
        "The purifier cleans the air best with the windows shut.",
        "खिड़कियाँ बंद हों तो प्यूरीफ़ायर हवा सबसे अच्छी साफ़ करता है।",
    ),
    ReasonCode.AIR_REFRESHED: (
        "The air is fresh again. Closing keeps the smog out.",
        "हवा फिर ताज़ी है। बंद करने से स्मॉग बाहर रहेगा।",
    ),
    ReasonCode.COLD_LIMIT: (
        "It's cold outside, so the windows stay open only as long as needed.",
        "बाहर ठंड है, इसलिए खिड़कियाँ बस ज़रूरत भर खुली रहेंगी।",
    ),
    ReasonCode.POLICY_FORBIDS_OPEN: (
        "Outside air is severe. School policy keeps the windows mostly shut.",
        "बाहर की हवा गंभीर है। स्कूल नीति के अनुसार खिड़कियाँ ज़्यादातर बंद रहेंगी।",
    ),
    ReasonCode.ATTENTION_BUDGET: (
        "Fewer changes today, so you're not interrupted too often.",
        "आज कम बदलाव, ताकि पढ़ाई में बार-बार रुकावट न हो।",
    ),
    ReasonCode.KEEP_STEADY: ("All fine. Keep things as they are.", "सब ठीक है। जैसा है वैसा रहने दीजिए।"),
}

FOLLOW_UP_TEXT: dict[str, tuple[str, str]] = {
    "other_side": (
        "Only one side seems open. Open the corridor side too.",
        "लगता है एक ही तरफ़ खुली है। कॉरिडोर वाली खिड़कियाँ भी खोलिए।",
    ),
    "not_changed": (
        "The air hasn't changed yet. Are the windows open?",
        "हवा अभी नहीं बदली। क्या खिड़कियाँ खुली हैं?",
    ),
    "gentle": ("When you have a moment:", "जब समय मिले:"),
}

STATUS_TEXT: dict[str, tuple[str, str]] = {
    "checking": ("Done. Checking the air…", "हो गया। हवा जाँच रहे हैं…"),
    "verified": ("Air is changing ✓", "हवा बदल रही है ✓"),
    "keep": ("All fine, keep them as they are", "सब ठीक है, जैसा है वैसा रखिए"),
}


def action_text(action: Action) -> tuple[str, str]:
    return ACTION_TEXT[(action.window, action.purifier)]


def done_button(prev: Action, action: Action) -> tuple[str, str]:
    order = list(Window)
    if order.index(action.window) > order.index(prev.window):
        return DONE_BUTTON["open"]
    if order.index(action.window) < order.index(prev.window):
        return DONE_BUTTON["close"]
    return DONE_BUTTON["purifier"]
