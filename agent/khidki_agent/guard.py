"""Number-fidelity guard: every number in an LLM answer must appear in that turn's tool outputs.

A number passes if some tool value is within one unit of its last decimal place, or, for a rounded whole
number (trailing zeros), within half its rounding unit and within 3% of the tool value. So a measured
1,623 ppm may be said as 1,623, 1,620 or 1,600, but 95 µg/m³ may not become 100.
Times (10:05) must match a tool time exactly. Numbers glued to letters (PM2.5, CO₂, 6B, S2) are names, not
claims, and are skipped. Devanagari digits are normalised first.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

DEVANAGARI = str.maketrans("०१२३४५६७८९", "0123456789")
_LETTER = r"A-Za-zऀ-ॣ०-ॿ₂"
TIME_RE = re.compile(r"(?<![\d:])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])")
NUM_RE = re.compile(rf"(?<![{_LETTER}\d.,])(\d{{1,3}}(?:,\d{{2,3}})+|\d+)(\.\d+)?(?![{_LETTER}\d])")


@dataclass
class GuardResult:
    ok: bool
    checked: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)


def _walk(x: Any, nums: list[float], times: set[str]) -> None:
    if isinstance(x, bool):
        return
    if isinstance(x, (int, float)):
        nums.append(float(x))
    elif isinstance(x, str):
        s = x.translate(DEVANAGARI)
        for h, m in TIME_RE.findall(s):
            times.add(f"{int(h):02d}:{m}")
        for whole, frac in NUM_RE.findall(TIME_RE.sub(" ", s)):
            nums.append(float(whole.replace(",", "") + (frac or "")))
    elif isinstance(x, dict):
        for v in x.values():
            _walk(v, nums, times)
    elif isinstance(x, (list, tuple)):
        for v in x:
            _walk(v, nums, times)


def evidence(tool_outputs: list[Any]) -> tuple[list[float], set[str]]:
    nums: list[float] = []
    times: set[str] = set()
    for out in tool_outputs:
        _walk(json.loads(out) if isinstance(out, str) and out[:1] in "{[" else out, nums, times)
    return nums, times


def _close(v: float, value: float, whole: str, frac: str) -> bool:
    decimals = len(frac) - 1 if frac else 0
    unit = 10.0**-decimals
    if abs(v - value) <= unit + 1e-9:
        return True
    digits = whole.replace(",", "")
    trailing = len(digits) - len(digits.rstrip("0")) if not frac and value else 0
    if trailing == 0:
        return False
    diff = abs(v - value)
    return diff <= 10.0**trailing / 2 and diff <= 0.03 * abs(v)


def check(answer: str, tool_outputs: list[Any]) -> GuardResult:
    nums, times = evidence(tool_outputs)
    text = answer.translate(DEVANAGARI)
    res = GuardResult(ok=True)
    for h, m in TIME_RE.findall(text):
        t = f"{int(h):02d}:{m}"
        res.checked.append(t)
        if t not in times:
            res.unsupported.append(t)
    for whole, frac in NUM_RE.findall(TIME_RE.sub(" ", text)):
        token = whole + (frac or "")
        value = float(whole.replace(",", "") + (frac or ""))
        res.checked.append(token)
        if not any(_close(v, value, whole, frac) for v in nums):
            res.unsupported.append(token)
    res.ok = not res.unsupported
    return res
