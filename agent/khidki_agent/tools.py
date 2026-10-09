"""Read-only, deterministic tools. Every one returns JSON-able numbers. None of them changes a plan."""

from __future__ import annotations

from typing import Any

import numpy as np

from khidki_core import aqi
from khidki_core.clock import ist_minute
from khidki_core.policy import POLICIES
from khidki_core.schemas import Plan, ReasonCode
from khidki_core.timetable import default_timetable, hhmm, parse_hhmm
from khidki_services import texts
from khidki_services.engine import Engine
from khidki_services.policy import ActivityContext

IR_SEATED_M3_H = 0.5  # seated child (US EPA Exposure Factors Handbook, ch. 6)
IR_PE_M3_H = 1.2  # moderate activity, child (same source, rounded)


class Tools:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_room_now(self, room_id: str) -> dict[str, Any]:
        v = self.engine.room_now(room_id)
        card = v["card"]
        out: dict[str, Any] = {
            "room": room_id,
            "time": v["clock"]["time"],
            "co2_ppm": v["indoor"]["co2"],
            "indoor_pm25": v["indoor"]["pm25"],
            "outdoor_pm25": v["outdoor"]["pm25"],
            "outdoor_aqi": v["outdoor"]["aqi"],
            "aqi_category_en": v["outdoor"]["category_en"],
            "aqi_category_hi": v["outdoor"]["category_hi"],
            "window_now": v["window"]["inferred"],
            "simulated": True,
        }
        if card["kind"] == "action":
            out["current_instruction"] = {
                "en": card["text"]["en"],
                "hi": card["text"]["hi"],
                "duration_min": card["duration_min"],
                "reason_code": card["reason_code"],
            }
        elif card.get("next"):
            out["next_change"] = {
                "time": card["next"]["t"],
                "en": card["next"]["text"]["en"],
                "hi": card["next"]["text"]["hi"],
                "reason_code": card["next"]["reason_code"],
            }
        return out

    def get_outdoor_forecast(self, hours: int = 3) -> dict[str, Any]:
        day = self.engine.day()
        fc = self.engine.forecast(day["date"])
        now = ist_minute(self.engine.clock.now())
        rows = [
            {"time": hhmm(int(m)), "pm25": round(float(p))}
            for m, p in zip(fc.hour_min, fc.pm25, strict=True)
            if now - 60 < m <= now + hours * 60 and np.isfinite(p)
        ]
        return {
            "hourly": rows,
            "city_aqi": day["city_aqi"],
            "indicative_grap_stage": day["grap_stage"],
            "source": fc.source,
        }

    def get_plan(self, room_id: str) -> dict[str, Any]:
        item = self.engine.current_plan(room_id)
        if not item:
            return {"instructions": []}
        plan = Plan.model_validate(item["plan"])
        return {
            "instructions": [
                {
                    "time": i.t_start,
                    "duration_min": i.duration_min,
                    "en": texts.action_text(i.action)[0],
                    "hi": texts.action_text(i.action)[1],
                    "reason_code": i.reason_code.value,
                }
                for i in plan.instructions
            ],
            "max_changes_per_day": self.engine.school.max_changes,
        }

    def check_activity(
        self, room_id: str, start: str | None = None, duration_min: int = 35
    ) -> dict[str, Any]:
        """Should the class go outside (PE) at `start`? Cedar decides; this explains with numbers."""
        cfg = self.engine.room_cfg(room_id)
        if start is None:
            slot = next((s for s in default_timetable() if s.name == f"Period {cfg.pe_period}"), None)
            start = hhmm(slot.start_min) if slot else "11:15"
        a = parse_hhmm(start)
        b = a + duration_min
        fc = self.engine.forecast(self.engine.clock.date())
        grid = np.arange(a, b + 1, 5)
        pm_out = np.interp(grid, fc.hour_min, fc.pm25)
        max_pm = float(np.max(np.interp(np.arange(a - 59, b + 1, 5), fc.hour_min, fc.pm25)))
        stage = self.engine.day()["grap_stage"]
        decision = self.engine.policy.activity(
            ActivityContext(kind="pe", max_pm25_during=max_pm, grap_stage=stage, min_grade=cfg.grade)
        )
        indoor = self._indoor_pm(room_id, a, b)
        hours = duration_min / 60
        fired = [p for p in decision.policy_ids if p in POLICIES and p.startswith("S")]
        return {
            "start": start,
            "end": hhmm(b),
            "allowed_outside": decision.allowed,
            "policy_ids": list(decision.policy_ids),
            "policy_text": {p: {"en": POLICIES[p].en, "hi": POLICIES[p].hi} for p in fired},
            "outdoor_pm25_max": round(max_pm),
            "outdoor_pm25_mean": round(float(np.mean(pm_out))),
            "outdoor_aqi": aqi.pm25_subindex(float(np.mean(pm_out))),
            "indoor_pm25_mean": None if indoor is None else round(indoor),
            "dose_outside_ug": round(float(np.mean(pm_out)) * IR_PE_M3_H * hours),
            "dose_inside_ug": None if indoor is None else round(indoor * IR_SEATED_M3_H * hours),
            "grap_stage": stage,
            "simulated": True,
        }

    def _indoor_pm(self, room_id: str, a: int, b: int) -> float | None:
        item = self.engine.current_plan(room_id)
        if not item:
            return None
        steps = [s for s in item["plan"]["steps"] if a <= s["t_min"] < b]
        return float(np.mean([s["predicted_pm"] for s in steps])) if steps else None

    def explain_reason_code(self, code: str) -> dict[str, Any]:
        en, hi = texts.REASON_TEXT[ReasonCode(code)]
        return {"code": code, "en": en, "hi": hi}
