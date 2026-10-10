"""Khidki's domain engine: morning plan, telemetry, re-planning, nudges and the views the screens read.

Everything stateful lives in the Store (so Lambda handlers can call the same methods statelessly); the clock,
outdoor data and policy are injected.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

import numpy as np

from khidki_core import aqi, grap
from khidki_core.clock import IST, SimClock, ist_epoch, ist_minute
from khidki_core.inference import (
    CO2_GAIN,
    PM_GAIN,
    Verdict,
    WindowGuess,
    blend,
    classify_window,
    fit_ach,
    verify_ventilation,
)
from khidki_core.optimizer import Grid
from khidki_core.physics import co2_source_ppm_per_h, relax
from khidki_core.planning import build_plan
from khidki_core.policy import POLICIES
from khidki_core.schemas import (
    WINDOW_ORDER,
    Action,
    Constraint,
    Kpis,
    Plan,
    Profile,
    Purifier,
    ReasonCode,
    RoomParams,
    Window,
)
from khidki_core.timetable import DAY_END_MIN, DAY_START_MIN, PLAN_DT_MIN, default_timetable, hhmm, occupancy
from khidki_data.bias import bias_ratio
from khidki_data.replay import build_drive
from khidki_services import nudge as nsm
from khidki_services import texts
from khidki_services.outdoor import OutdoorDay, OutdoorProvider
from khidki_services.policy import ActivityContext, CedarPolicyEngine, PolicyEngine
from khidki_services.seed import DEMO_SCHOOL, RoomConfig, SchoolConfig
from khidki_services.store import Item, Store

REPLAN_EVERY_S = 300.0
COOLDOWN_AFTER_MISS_S = 300.0
DAY_CACHE_S = 20.0
"""How long a warm Lambda trusts its copy of today's decisions (overrides from other containers show up
within this time)."""
EMPTY_ROOM_MIN_EXCESS_PPM = 150.0
TEL_TTL_S = 14 * 24 * 3600
ACTIVITIES = (
    ("assembly", "Assembly", 7 * 60 + 30, 7 * 60 + 50),
    ("recess_outdoor", "Recess outdoors", 10 * 60 + 10, 10 * 60 + 40),
)


def iso(epoch_s: float) -> str:
    return dt.datetime.fromtimestamp(epoch_s, tz=dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4] + "Z"


def _action_json(a: Action) -> dict[str, str]:
    return {"window": a.window.value, "purifier": a.purifier.value}


def _action(d: dict[str, str]) -> Action:
    return Action(window=Window(d["window"]), purifier=Purifier(d["purifier"]))


NudgeHook = Callable[[str, dict[str, Any]], None]


def change_reason(before: Action, after: Action, kids_present: bool) -> ReasonCode:
    """Why the windows or purifier are being changed, judged from the change itself.

    A plan step that continues the previous step is labelled KEEP_STEADY. After a re-plan, or when plans
    from different times of day are stitched together, the step where the teacher is actually asked to act
    can carry that label, and "All fine, keep things as they are" under "Open the windows" is wrong. This
    gives the honest reason for the direction of the change instead.
    """
    order = list(Window)
    if after.window == before.window:
        return ReasonCode.PURIFIER_DURING_CLOSED
    if order.index(after.window) > order.index(before.window):
        return ReasonCode.CO2_RISING_FAST if kids_present else ReasonCode.RECESS_PURGE
    if after.window == Window.CLOSED and after.purifier == Purifier.ON:
        return ReasonCode.PURIFIER_DURING_CLOSED
    return ReasonCode.AIR_REFRESHED


class Engine:
    def __init__(
        self,
        store: Store,
        clock: SimClock,
        outdoor: OutdoorProvider,
        policy: PolicyEngine | None = None,
        school: SchoolConfig = DEMO_SCHOOL,
        grid: Grid | None = None,
        replan_every_s: float = REPLAN_EVERY_S,
        external_nudges: bool = False,
    ) -> None:
        self.store = store
        self.clock = clock
        self.outdoor = outdoor
        self.policy = policy if policy is not None else CedarPolicyEngine(school)
        self.school = school
        self.grid = grid
        self.replan_every_s = replan_every_s
        self.on_nudge: list[NudgeHook] = []
        self.on_ack: list[NudgeHook] = []
        self.external_nudges = external_nudges
        """True in the cloud: Step Functions owns nudge timing (waits, timeouts, verification)."""
        self.task_notifier: Callable[[str, Item], None] | None = None
        """Returns the teacher's tap to a waiting Step Functions task (SendTaskSuccess)."""
        self._forecast_cache: dict[str, OutdoorDay] = {}
        self._day_cache: dict[str, tuple[float, Item]] = {}

    # ── setup ────────────────────────────────────────────────────────────────────────────────────────
    def seed(self) -> None:
        s = self.school
        self.store.put(
            f"SCHOOL#{s.school_id}",
            "META",
            {
                "name": s.name,
                "lat": s.lat,
                "lon": s.lon,
                "nearest_station": s.nearest_station,
                "max_changes": s.max_changes,
                "official_grap_stage": None,
            },
        )
        for r in s.rooms:
            self.store.put(
                f"SCHOOL#{s.school_id}",
                f"ROOM#{r.room_id}",
                {
                    "room_id": r.room_id,
                    "name": r.name,
                    "grade": r.grade,
                    "students": r.params.students,
                    "has_purifier": r.params.has_purifier,
                    "sensitive_count": r.sensitive_count,
                    "pe_period": r.pe_period,
                    "tier": r.tier,
                    "frame_paint": r.frame_paint,
                    "params": r.params.model_dump(mode="json"),
                },
            )
            self.store.put(
                f"ROOM#{r.room_id}",
                "STATE",
                {
                    "co2": 550.0,
                    "pm25": None,
                    "estimate_at": None,
                    "believed": _action_json(Action(window=Window.CLOSED)),
                    "inferred": {"window": "closed", "confidence": 0.5, "pending": None},
                    "open_nudge": None,
                    "last_replan_at": None,
                    "plan_sk": None,
                    "cooldown_until": 0.0,
                    "last_ingest": None,
                    "last_outcome": None,
                    "counts": {},
                },
            )

    def room_cfg(self, room_id: str) -> RoomConfig:
        return self.school.room(room_id)

    def params(self, room_id: str) -> RoomParams:
        item = self.store.get(f"SCHOOL#{self.school.school_id}", f"ROOM#{room_id}")
        if item is None:
            return self.room_cfg(room_id).params
        return RoomParams.model_validate(item["params"])

    def _state(self, room_id: str) -> Item:
        self.room_cfg(room_id)  # unknown room -> KeyError (a 404 at the API), never a re-seed
        st = self.store.get(f"ROOM#{room_id}", "STATE")
        if st is None:
            self.seed()
            st = self.store.get(f"ROOM#{room_id}", "STATE")
        assert st is not None
        return st

    def _put_state(self, room_id: str, st: Item) -> None:
        self.store.put(f"ROOM#{room_id}", "STATE", st)

    # ── the day: forecast, GRAP, activity decisions ──────────────────────────────────────────────────
    def forecast(self, date: str) -> OutdoorDay:
        if date not in self._forecast_cache:
            self._forecast_cache[date] = self.outdoor.forecast(date)
        return self._forecast_cache[date]

    def day(self) -> Item:
        date = self.clock.date()
        cached = self._day_cache.get(date)
        if cached and time.monotonic() - cached[0] < DAY_CACHE_S:
            return cached[1]
        pk = f"SCHOOL#{self.school.school_id}"
        item = self.store.get(pk, f"DAY#{date}")
        if item is not None:
            self._day_cache[date] = (time.monotonic(), item)
            return item
        fc = self.forecast(date)
        meta = self.store.get(pk, "META") or {}
        city_aqi = aqi.pm25_subindex(float(np.nanmean(fc.pm25)))
        indicative = grap.indicative_stage(city_aqi)
        stage = grap.effective_stage(indicative, meta.get("official_grap_stage"))
        decisions: list[Item] = []
        windows = [*ACTIVITIES]
        for r in self.school.rooms:
            if r.pe_period is not None:
                slot = next(s for s in default_timetable() if s.name == f"Period {r.pe_period}")
                windows.append((f"pe:{r.room_id}", f"PE ({r.room_id})", slot.start_min, slot.end_min))
        min_grade = min(r.grade for r in self.school.rooms)
        for key, label, a, b in windows:
            mask = (fc.hour_min >= a - 59) & (fc.hour_min < b)
            max_pm = float(np.nanmax(fc.pm25[mask])) if mask.any() else float(np.nanmax(fc.pm25))
            grade = self.room_cfg(key.split(":")[1]).grade if key.startswith("pe:") else min_grade
            kind = "pe" if key.startswith("pe:") else key
            d = self.policy.activity(
                ActivityContext(kind=kind, max_pm25_during=max_pm, grap_stage=stage, min_grade=grade)
            )
            decisions.append(
                {
                    "key": key,
                    "label": label,
                    "start": hhmm(a),
                    "end": hhmm(b),
                    "outdoor": d.allowed,
                    "policy_ids": list(d.policy_ids),
                    "max_pm25": round(max_pm),
                    "override": None,
                }
            )
        item = {
            "date": date,
            "city_aqi": city_aqi,
            "indicative_grap": indicative,
            "grap_stage": stage,
            "forecast_source": fc.source,
            "simulated": fc.simulated,
            "decisions": decisions,
            "hourly": {
                "hour_min": fc.hour_min.tolist(),
                "pm25": [None if np.isnan(x) else round(float(x), 1) for x in fc.pm25],
            },
        }
        self.store.put(pk, f"DAY#{date}", item)
        self._day_cache[date] = (time.monotonic(), item)
        return item

    def _decided(self, day: Item, key: str) -> bool:
        for d in day["decisions"]:
            if d["key"] == key:
                return bool(d["override"] if d["override"] is not None else d["outdoor"])
        return True

    def occupancy_flags(self, room_id: str) -> dict[str, Any]:
        day = self.day()
        r = self.room_cfg(room_id)
        return {
            "assembly_outdoor": self._decided(day, "assembly"),
            "recess_outdoor": self._decided(day, "recess_outdoor"),
            "pe_period": r.pe_period,
            "pe_outdoor": self._decided(day, f"pe:{room_id}") if r.pe_period else False,
        }

    def occupants_at(self, room_id: str, minute: float) -> tuple[float, float]:
        p = self.params(room_id)
        kids, adults = occupancy(
            np.array([int(minute)], dtype=np.int64), p.students, p.adults, **self.occupancy_flags(room_id)
        )
        return float(kids[0]), float(adults[0])

    # ── outdoor observation and bias ─────────────────────────────────────────────────────────────────
    def _bias(self) -> tuple[float, bool]:
        pk = f"SCHOOL#{self.school.school_id}"
        obs = self.store.query(pk, f"OBS#{self.clock.date()}", limit=6, newest_first=True)
        if not obs:
            return 1.0, False
        fc = self.forecast(self.clock.date())
        o = [x["pm25"] for x in obs]
        f = [float(np.interp(x["minute"], fc.hour_min, fc.pm25)) for x in obs]
        r = bias_ratio(o, f)
        return r.ratio, r.corrected

    def observe_outdoor(self) -> None:
        now = self.clock.now()
        pk = f"SCHOOL#{self.school.school_id}"
        last = self.store.query(pk, f"OBS#{self.clock.date()}", limit=1, newest_first=True)
        if last and now - last[0]["at"] < 300:
            return
        pm = self.outdoor.observe(now)
        if pm is not None:
            self.store.put(
                pk, f"OBS#{self.clock.date()}#{iso(now)}", {"at": now, "minute": ist_minute(now), "pm25": pm}
            )

    # ── telemetry ────────────────────────────────────────────────────────────────────────────────────
    def ingest(self, room_id: str, reading: dict[str, Any], infer: bool = True) -> Item:
        """Store a reading and update the state estimate. `infer=False` skips the CO₂-curve fit (a batch only
        needs it on its newest reading per room)."""
        ts = float(reading.get("ts") or self.clock.now())
        item = {
            "ts": ts,
            "co2": float(reading["co2"]),
            "pm25": None if reading.get("pm25") is None else float(reading["pm25"]),
            "temp": reading.get("temp"),
            "simulated": bool(reading.get("simulated", True)),
            "ttl": int(ts + TEL_TTL_S),
        }
        self.store.put(f"ROOM#{room_id}", f"TEL#{iso(ts)}", item)
        st = self._state(room_id)
        params = self.params(room_id)
        minute = ist_minute(ts)
        kids, adults = self.occupants_at(room_id, minute)
        # State estimate: predict from the last estimate with the believed action, then blend.
        if st["estimate_at"] is not None and ts > st["estimate_at"]:
            dt_h = (ts - st["estimate_at"]) / 3600.0
            act = _action(st["believed"])
            lam = params.lam[act.window]
            fc = self.forecast(self.clock.date())
            pm_out = float(np.interp(minute, fc.hour_min, fc.pm25))
            src = float(co2_source_ppm_per_h(kids, adults, params))
            c_pred = float(relax(st["co2"], lam, lam * 450 + src, dt_h)[0])
            q = (
                params.purifier_cadr_m3_h * params.purifier_effectiveness
                if act.purifier == Purifier.ON
                else 0.0
            )
            a = lam + params.deposition_per_h + q / params.volume_m3
            p_prev = st["pm25"] if st["pm25"] is not None else item["pm25"] or 0.0
            p_pred = float(relax(p_prev, a, params.pen[act.window] * lam * pm_out, dt_h)[0])
        else:
            c_pred, p_pred = item["co2"], item["pm25"] if item["pm25"] is not None else 0.0
        st["co2"] = round(blend(c_pred, item["co2"], CO2_GAIN), 1)
        st["pm25"] = None if item["pm25"] is None else round(blend(p_pred, item["pm25"], PM_GAIN), 1)
        st["estimate_at"] = ts
        st["last_ingest"] = ts
        # Window inference from the last 4.5 minutes at constant occupancy.
        fit = self._fit_recent(room_id, ts - 270, ts, kids, adults) if infer else None
        if fit is not None:
            guess = classify_window(fit.lam, params.lam)
            inf = st["inferred"]
            if guess.window.value == inf["window"]:
                inf.update(confidence=guess.confidence, pending=None)
            elif guess.confidence >= 0.75 or inf.get("pending") == guess.window.value:
                inf.update(window=guess.window.value, confidence=guess.confidence, pending=None)
            else:
                inf["pending"] = guess.window.value
            inf["lam"] = round(fit.lam, 2)
        self._put_state(room_id, st)
        return item

    def telemetry(self, room_id: str, since: float, until: float | None = None) -> list[Item]:
        rows = self.store.query(f"ROOM#{room_id}", "TEL#", sk_from=f"TEL#{iso(since)}")
        return [r for r in rows if until is None or r["ts"] <= until]

    def _fit_recent(self, room_id: str, since: float, until: float, kids: float, adults: float) -> Any:
        rows = [
            r
            for r in self.telemetry(room_id, since, until)
            if self.occupants_at(room_id, ist_minute(r["ts"])) == (kids, adults)
        ]
        if len(rows) < 6:
            return None
        if kids == 0 and adults == 0 and np.mean([r["co2"] for r in rows]) < 450 + EMPTY_ROOM_MIN_EXCESS_PPM:
            return None  # empty room at outdoor level: the curve carries no information about the window
        params = self.params(room_id)
        t_h = np.array([r["ts"] for r in rows]) / 3600.0
        co2 = np.array([r["co2"] for r in rows])
        src = float(co2_source_ppm_per_h(kids, adults, params))
        return fit_ach(t_h, co2, 450.0, src)

    # ── planning ─────────────────────────────────────────────────────────────────────────────────────
    def constraints(self, room_id: str) -> list[Constraint]:
        rows = self.store.query(f"ROOM#{room_id}", f"CONSTRAINT#{self.clock.date()}")
        return [Constraint.model_validate(r["constraint"]) for r in rows]

    def replan(self, room_id: str, reason: str = "scheduled") -> Plan | None:
        now = self.clock.now()
        minute = int(ist_minute(now))
        start = max(DAY_START_MIN, minute - minute % PLAN_DT_MIN)
        if start >= DAY_END_MIN:
            return None
        day = self.day()
        st = self._state(room_id)
        params = self.params(room_id)
        fc = self.forecast(day["date"])
        ratio, corrected = self._bias()
        lead_h = np.maximum(fc.hour_min - minute, 0) / 60.0
        pm = fc.pm25 * (1 + (ratio - 1) * np.exp(-lead_h / 12.0))
        drive = build_drive(
            fc.hour_min, pm, fc.temp, fc.co2, params, start_min=start, **self.occupancy_flags(room_id)
        )
        prev = _action(st["believed"])
        stage = day["grap_stage"]
        profile = Profile.LUNGS_FIRST if stage >= 3 else Profile.BALANCED
        cfg = self.room_cfg(room_id)
        old = self.store.get(f"ROOM#{room_id}", st["plan_sk"]) if st["plan_sk"] else None
        version = (old["plan"]["version"] + 1) if old and old["plan"]["date"] == day["date"] else 1
        changes_left = self.school.max_changes - int(st["counts"].get(f"issued:{day['date']}", 0))
        plan, res = build_plan(
            room_id,
            day["date"],
            params,
            drive,
            co2_0=float(st["co2"]),
            pm_0=float(st["pm25"] if st["pm25"] is not None else pm[0] * 0.6),
            prev_action=prev,
            profile=profile,
            max_changes=max(changes_left, 0),
            constraints=self.constraints(room_id),
            mask_fn=lambda d, aa: self.policy.ventilation_mask(d, aa, stage),
            version=version,
            with_baselines=(version == 1),
        )
        if old and version > 1 and not plan.baselines_predicted:
            plan.baselines_predicted = {
                k: Kpis.model_validate(v) for k, v in old["plan"]["baselines_predicted"].items()
            }
        sk = f"PLAN#{day['date']}#v{version:03d}"
        self.store.put(
            f"ROOM#{room_id}",
            sk,
            {
                "plan": plan.model_dump(mode="json"),
                "reason": reason,
                "made_at": now,
                "bias_ratio": round(ratio, 2),
                "bias_corrected": corrected,
                "seconds": round(res.seconds, 2),
                "sensitive": cfg.sensitive_count,
            },
        )
        st = self._state(room_id)
        st["plan_sk"], st["last_replan_at"] = sk, now
        self._put_state(room_id, st)
        return plan

    def current_plan(self, room_id: str) -> Item | None:
        st = self._state(room_id)
        return self.store.get(f"ROOM#{room_id}", st["plan_sk"]) if st["plan_sk"] else None

    # ── nudges ───────────────────────────────────────────────────────────────────────────────────────
    def tick(self, room_ids: list[str] | None = None) -> None:
        """Advance everything to clock.now(): outdoor observation, re-plans, nudge timeouts and checks.

        `room_ids` limits the work to some rooms (the cloud ticks one room per ingested reading)."""
        now = self.clock.now()
        minute = ist_minute(now)
        if minute < DAY_START_MIN or minute >= DAY_END_MIN:
            return
        self.day()
        self.observe_outdoor()
        for r in self.school.rooms:
            rid = r.room_id
            if room_ids is not None and rid not in room_ids:
                continue
            st = self._state(rid)
            if st["last_replan_at"] is None or now - st["last_replan_at"] >= self.replan_every_s:
                self.replan(rid)
            st = self._state(rid)
            if st["open_nudge"]:
                if not self.external_nudges:
                    self._advance_nudge(rid, st["open_nudge"], now)
            elif now >= st["cooldown_until"]:
                self._maybe_issue(rid, now, minute)

    def _maybe_issue(self, room_id: str, now: float, minute: float) -> None:
        item = self.current_plan(room_id)
        if not item:
            return
        plan = Plan.model_validate(item["plan"])
        st = self._state(room_id)
        if int(st["counts"].get(f"issued:{plan.date}", 0)) >= self.school.max_changes:
            return  # attention budget spent for today: stay quiet
        kids_now, _ = self.occupants_at(room_id, minute)
        kids_before, _ = self.occupants_at(room_id, minute - PLAN_DT_MIN)
        if kids_now == 0 and kids_before == 0:
            return  # nobody in the room to make the change; re-plan when the class is back
        believed = _action(st["believed"])
        step = next((s for s in plan.steps if s.t_min <= minute < s.t_min + PLAN_DT_MIN), None)
        if step is None:
            return
        target = Action(window=step.window, purifier=step.purifier)
        if target == believed:
            return
        instr = next((i for i in plan.instructions if i.t_start_min <= minute < i.t_end_min), None)
        duration = (instr.t_end_min - int(minute)) if instr else PLAN_DT_MIN
        reason = instr.reason_code if instr else step.reason_code
        if reason == ReasonCode.KEEP_STEADY:  # the plan step continues an earlier one, but we are asking
            reason = change_reason(believed, target, kids_now > 0)
        verifiable = target.window != believed.window
        state = nsm.issue(now, verifiable=verifiable)
        nid = f"{room_id}-{int(now)}"
        en, hi = texts.action_text(target)
        b_en, b_hi = texts.done_button(believed, target)
        r_en, r_hi = texts.REASON_TEXT[reason]
        nudge = {
            "nudge_id": nid,
            "room_id": room_id,
            "issued_at": now,
            "issued_t": hhmm(int(minute)),
            "from": _action_json(believed),
            "action": _action_json(target),
            "duration_min": int(duration),
            "reason_code": reason.value,
            "text": {"en": en, "hi": hi},
            "button": {"en": b_en, "hi": b_hi},
            "reason": {"en": r_en, "hi": r_hi},
            "plan_version": plan.version,
            "state": asdict(state),
            "evidence": None,
            "simulated": True,
        }
        self.store.put(f"ROOM#{room_id}", f"NUDGE#{iso(now)}", nudge)
        st["open_nudge"] = f"NUDGE#{iso(now)}"
        st["counts"][f"issued:{plan.date}"] = int(st["counts"].get(f"issued:{plan.date}", 0)) + 1
        self._put_state(room_id, st)
        for hook in self.on_nudge:
            hook(room_id, nudge)

    def _load_nudge(self, room_id: str, sk: str) -> tuple[Item, nsm.NudgeState]:
        n = self.store.get(f"ROOM#{room_id}", sk)
        assert n is not None
        s = n["state"]
        state = nsm.NudgeState(
            **{
                **s,
                "status": nsm.Status(s["status"]),
                "follow_up": nsm.FollowUp(s["follow_up"]) if s["follow_up"] else None,
                "outcome": nsm.Outcome(s["outcome"]) if s["outcome"] else None,
                "history": tuple(s["history"]),
            }
        )
        return n, state

    def _save_nudge(self, room_id: str, sk: str, n: Item, state: nsm.NudgeState) -> None:
        n["state"] = asdict(state)
        self.store.put(f"ROOM#{room_id}", sk, n)

    def find_nudge(self, nudge_id: str) -> tuple[str, str]:
        room_id, _ = nudge_id.rsplit("-", 1)
        st = self._state(room_id)
        sk = st["open_nudge"]
        if sk:
            n = self.store.get(f"ROOM#{room_id}", sk)
            if n and n["nudge_id"] == nudge_id:
                return room_id, sk
        for n in self.store.query(f"ROOM#{room_id}", "NUDGE#", newest_first=True, limit=20):
            if n["nudge_id"] == nudge_id:
                return room_id, n["sk"]
        raise KeyError(nudge_id)

    def ack(self, nudge_id: str, result: str, reason: str | None = None) -> Item:
        if result not in ("done", "cant"):
            raise ValueError("result must be 'done' or 'cant'")
        if result == "cant" and reason not in texts.CANT_REASONS:
            raise ValueError(f"reason must be one of {sorted(texts.CANT_REASONS)}")
        room_id, sk = self.find_nudge(nudge_id)
        n, state = self._load_nudge(room_id, sk)
        now = self.clock.now()
        new, effects = nsm.on_ack(state, now, result, reason)
        if new == state:  # a late or repeated tap changes nothing
            return n
        n["acked_at"] = now
        token = n.pop("task_token", None)
        self._save_nudge(room_id, sk, n, new)
        for hook in self.on_ack:
            hook(room_id, {**n, "ack": result, "cant_reason": reason})
        self._apply(room_id, sk, n, new, effects, now)
        if token and self.task_notifier:
            self.task_notifier(token, {"result": result, "reason": reason, "status": new.status.value})
        return self.store.get(f"ROOM#{room_id}", sk) or n

    # ── Step Functions entry points (cloud): same pure transitions as local mode ─────────────────────
    def nudge_seconds(self) -> dict[str, int]:
        """Real seconds Step Functions should wait (simulated seconds divided by the demo speed)."""
        return {
            "ack_timeout_s": max(1, round(self.clock.real_seconds(nsm.ACK_TIMEOUT_S))),
            "verify_wait_s": max(1, round(self.clock.real_seconds(nsm.VERIFY_WAIT_S))),
        }

    def _nudge_view(self, n: Item, state: nsm.NudgeState) -> Item:
        return {
            "nudge_id": n["nudge_id"],
            "status": state.status.value,
            "outcome": state.outcome.value if state.outcome else None,
            "follow_up": state.follow_up.value if state.follow_up else None,
            "ack": state.ack,
            "evidence": n.get("evidence"),
            **self.nudge_seconds(),
        }

    def sf_await_ack(self, nudge_id: str, token: str) -> Item:
        """Park the task token on the nudge. If the teacher has already tapped, hand it straight back."""
        room_id, sk = self.find_nudge(nudge_id)
        n, state = self._load_nudge(room_id, sk)
        if state.status in (nsm.Status.ISSUED, nsm.Status.FOLLOW_UP):
            n["task_token"] = token
            self._save_nudge(room_id, sk, n, state)
        elif self.task_notifier:
            self.task_notifier(
                token,
                {"result": state.ack or "done", "reason": state.cant_reason, "status": state.status.value},
            )
        return self._nudge_view(n, state)

    def sf_timeout(self, nudge_id: str) -> Item:
        """Nobody tapped in time: move to verification, exactly as the local tick would."""
        room_id, sk = self.find_nudge(nudge_id)
        n, state = self._load_nudge(room_id, sk)
        n.pop("task_token", None)
        new, effects = nsm.on_tick(state, max(self.clock.now(), state.deadline))
        self._save_nudge(room_id, sk, n, new)
        self._apply(room_id, sk, n, new, effects, self.clock.now())
        return self._nudge_view(n, new)

    def sf_verify(self, nudge_id: str) -> Item:
        """Read the CO₂ curve and decide: verified, follow up once, or not followed."""
        room_id, sk = self.find_nudge(nudge_id)
        n, state = self._load_nudge(room_id, sk)
        if state.status != nsm.Status.VERIFYING:
            return self._nudge_view(n, state)
        now = self.clock.now()
        verdict, evidence = self._verify(room_id, n, state, now)
        n["evidence"] = evidence
        new, effects = nsm.on_verdict(state, now, verdict)
        if new.status == nsm.Status.FOLLOW_UP and new.follow_up is not None:
            f_en, f_hi = texts.FOLLOW_UP_TEXT[new.follow_up.value]
            n["follow_up_text"] = {"en": f_en, "hi": f_hi}
        self._save_nudge(room_id, sk, n, new)
        self._apply(room_id, sk, n, new, effects, now)
        return self._nudge_view(n, new)

    def _advance_nudge(self, room_id: str, sk: str, now: float) -> None:
        n, state = self._load_nudge(room_id, sk)
        new, effects = nsm.on_tick(state, now)
        if nsm.Effect.VERIFY_NOW in effects:
            verdict, evidence = self._verify(room_id, n, new, now)
            n["evidence"] = evidence
            new, effects = nsm.on_verdict(new, now, verdict)
            if new.status == nsm.Status.FOLLOW_UP and new.follow_up is not None:
                f_en, f_hi = texts.FOLLOW_UP_TEXT[new.follow_up.value]
                n["follow_up_text"] = {"en": f_en, "hi": f_hi}
        if new != state or effects:
            self._save_nudge(room_id, sk, n, new)
            self._apply(room_id, sk, n, new, effects, now)

    def _verify(self, room_id: str, n: Item, state: nsm.NudgeState, now: float) -> tuple[Verdict, Item]:
        target = _action(n["action"])
        kids, adults = self.occupants_at(room_id, ist_minute(now))
        fit = self._fit_recent(room_id, max(state.verify_from, now - 240), now, kids, adults)
        params = self.params(room_id)
        if fit is None:
            verdict = Verdict.VERIFIED if state.ack == "done" else Verdict.NOT_CHANGED
            return verdict, {
                "note": "air data inconclusive (too few readings, or an empty room at outdoor "
                "CO₂); went by the teacher's tap",
                "n": 0,
            }
        v = verify_ventilation(target.window, fit, params.lam, previous=Window(n["from"]["window"]))
        return v.verdict, {
            "implied_lam": v.implied_lam,
            "expected_lam": v.expected_lam,
            "inferred": v.inferred.window.value,
            "confidence": v.inferred.confidence,
            "n": fit.n,
            "rmse": round(fit.rmse, 1),
        }

    def _apply(
        self, room_id: str, sk: str, n: Item, state: nsm.NudgeState, effects: list[nsm.Effect], now: float
    ) -> None:
        st = self._state(room_id)
        if nsm.Effect.RECORD_CONSTRAINT in effects and state.cant_reason:
            minute = int(ist_minute(now))
            end = {"rain": minute + 30, "cold": DAY_END_MIN}.get(state.cant_reason)
            if end is None:  # noise, exam: until the end of this period
                slot = next((s for s in default_timetable() if s.start_min <= minute < s.end_min), None)
                end = slot.end_min if slot else minute + 35
            c = Constraint(
                kind=state.cant_reason,
                start_min=minute,
                end_min=min(end, 24 * 60),
                window_at_start=_action(st["believed"]).window,
            )
            self.store.put(
                f"ROOM#{room_id}",
                f"CONSTRAINT#{self.clock.date()}#{iso(now)}",
                {"constraint": c.model_dump(mode="json"), "nudge_id": n["nudge_id"]},
            )
        if state.status == nsm.Status.DONE:
            outcome = state.outcome
            if outcome in (nsm.Outcome.VERIFIED, nsm.Outcome.VERIFIED_SILENT):
                st["believed"] = n["action"]
            elif outcome in (nsm.Outcome.PARTIAL, nsm.Outcome.NOT_FOLLOWED):
                inferred = (n.get("evidence") or {}).get("inferred") or st["inferred"]["window"]
                st["believed"] = {"window": inferred, "purifier": st["believed"]["purifier"]}
                st["cooldown_until"] = now + COOLDOWN_AFTER_MISS_S
            else:
                st["cooldown_until"] = now + COOLDOWN_AFTER_MISS_S
            st["open_nudge"] = None
            st["last_outcome"] = {
                "status": outcome.value if outcome else None,
                "at": now,
                "nudge_id": n["nudge_id"],
            }
            key = f"outcome:{outcome.value if outcome else 'none'}"
            st["counts"][key] = int(st["counts"].get(key, 0)) + 1
        self._put_state(room_id, st)
        if nsm.Effect.REPLAN in effects:
            self.replan(room_id, reason=f"nudge {state.outcome.value if state.outcome else 'update'}")

    # ── views ────────────────────────────────────────────────────────────────────────────────────────
    def clock_view(self) -> Item:
        s = self.clock.state
        return {
            "now": self.clock.now(),
            "time": self.clock.now_ist().strftime("%H:%M"),
            "date": self.clock.date(),
            "mode": s.mode.value,
            "speed": self.clock.speed,
            "simulated": self.clock.is_simulated,
        }

    def room_now(self, room_id: str) -> Item:
        now = self.clock.now()
        minute = ist_minute(now)
        st = self._state(room_id)
        cfg = self.room_cfg(room_id)
        params = self.params(room_id)
        fc = self.forecast(self.clock.date())
        pm_out = float(np.interp(minute, fc.hour_min, fc.pm25))
        obs = self.outdoor.observe(now)
        outdoor_now = obs if obs is not None else pm_out
        out_aqi = aqi.pm25_subindex(outdoor_now)
        cat = aqi.category_for_aqi(out_aqi)
        recent = self.telemetry(room_id, now - 3600, now)
        card: Item
        if st["open_nudge"]:
            n, s = self._load_nudge(room_id, st["open_nudge"])
            card = {
                "kind": "action",
                "nudge_id": n["nudge_id"],
                "action": n["action"],
                "from": n["from"],
                "text": n["text"],
                "button": n["button"],
                "reason": n["reason"],
                "reason_code": n["reason_code"],
                "duration_min": n["duration_min"],
                "status": s.status.value,
                "follow_up": s.follow_up.value if s.follow_up else None,
                "follow_up_text": n.get("follow_up_text"),
                "issued_at": n["issued_at"],
                "deadline": s.deadline,
                "acked_at": n.get("acked_at"),
            }
        else:
            nxt = None
            item = self.current_plan(room_id)
            if item:
                plan = Plan.model_validate(item["plan"])
                upcoming = [i for i in plan.instructions if i.t_start_min > minute]
                if upcoming:
                    i = upcoming[0]
                    en, hi = texts.action_text(i.action)
                    nxt = {
                        "t": i.t_start,
                        "action": _action_json(i.action),
                        "text": {"en": en, "hi": hi},
                        "reason_code": i.reason_code.value,
                    }
            k_en, k_hi = texts.STATUS_TEXT["keep"]
            card = {"kind": "keep", "text": {"en": k_en, "hi": k_hi}, "next": nxt}
        kids, _ = self.occupants_at(room_id, minute)
        return {
            "room_id": room_id,
            "name": cfg.name,
            "grade": cfg.grade,
            "has_purifier": params.has_purifier,
            "students": params.students,
            "frame_paint": cfg.frame_paint,
            "clock": self.clock_view(),
            "occupied": kids > 0,
            "outdoor": {
                "pm25": round(outdoor_now, 1),
                "aqi": out_aqi,
                "category": cat.key,
                "category_en": cat.name_en,
                "category_hi": cat.name_hi,
                "temp": round(float(np.interp(minute, fc.hour_min, fc.temp)), 1),
                "source": fc.source,
            },
            "indoor": {
                "co2": round(st["co2"]),
                "pm25": st["pm25"],
                "last_ingest": st["last_ingest"],
                "stale_s": None if st["last_ingest"] is None else round(now - st["last_ingest"]),
            },
            "window": {
                "believed": st["believed"],
                "inferred": st["inferred"]["window"],
                "confidence": st["inferred"]["confidence"],
                "implied_lam": st["inferred"].get("lam"),
            },
            "card": card,
            # the attention budget, shown to the teacher as a plain count ("2 of 6 requests used today")
            "requests": {
                "used": int(st["counts"].get(f"issued:{self.clock.date()}", 0)),
                "max": self.school.max_changes,
            },
            "last_outcome": st["last_outcome"],
            "series": [
                {"t": hhmm(int(ist_minute(r["ts"]))), "ts": r["ts"], "co2": r["co2"], "pm25": r["pm25"]}
                for r in recent[::2]
            ],
            "simulated": True,
        }

    def plan_view(self, room_id: str) -> Item | None:
        item = self.current_plan(room_id)
        if not item:
            return None
        return {
            **item["plan"],
            "made_at": item["made_at"],
            "reason": item["reason"],
            "bias_ratio": item["bias_ratio"],
            "bias_corrected": item["bias_corrected"],
            "day_steps": self.day_steps(room_id, item["plan"]["date"]),
            "timetable": self.timetable(room_id, item["plan"]["date"]),
        }

    def timetable(self, room_id: str, date: str) -> list[Item]:
        """The day's instructions as a printable list (the no-hardware tier), in both languages."""
        steps = self.day_steps(room_id, date)
        out: list[Item] = []
        prev: tuple[str, str] | None = None
        for st in steps:
            key = (st["window"], st["purifier"])
            if key != prev and prev is not None:
                action = Action(window=Window(st["window"]), purifier=Purifier(st["purifier"]))
                en, hi = texts.action_text(action)
                code = ReasonCode(st["reason_code"])
                if code == ReasonCode.KEEP_STEADY:  # a boundary between stitched plans: see change_reason
                    before = Action(window=Window(prev[0]), purifier=Purifier(prev[1]))
                    kids, _ = self.occupants_at(room_id, st["t_min"])
                    code = change_reason(before, action, kids > 0)
                r_en, r_hi = texts.REASON_TEXT[code]
                out.append(
                    {
                        "t": st["t"],
                        "t_min": st["t_min"],
                        "window": st["window"],
                        "purifier": st["purifier"],
                        "text": {"en": en, "hi": hi},
                        "reason": {"en": r_en, "hi": r_hi},
                    }
                )
            prev = key
        for i, row in enumerate(out):
            end = out[i + 1]["t_min"] if i + 1 < len(out) else DAY_END_MIN
            row["until"] = hhmm(end)
        return out

    def day_steps(self, room_id: str, date: str) -> list[Item]:
        """The whole day as planned: each plan version owns the steps from the moment it was made, so earlier
        steps keep what was planned at the time (the latest version only covers the rest of the day)."""
        by_t: dict[int, Item] = {}
        for item in self.store.query(f"ROOM#{room_id}", f"PLAN#{date}#"):
            for step in item["plan"]["steps"]:
                by_t[step["t_min"]] = step
        return [by_t[t] for t in sorted(by_t)]

    def school_today(self) -> Item:
        day = self.day()
        meta = self.store.get(f"SCHOOL#{self.school.school_id}", "META") or {}
        stage = grap.STAGES[day["grap_stage"]]
        rooms = []
        for r in self.school.rooms:
            now = self.room_now(r.room_id)
            rooms.append(
                {
                    k: now[k]
                    for k in (
                        "room_id",
                        "name",
                        "grade",
                        "has_purifier",
                        "frame_paint",
                        "indoor",
                        "window",
                        "card",
                        "last_outcome",
                        "occupied",
                    )
                }
            )
        return {
            "school_id": self.school.school_id,
            "name": meta.get("name", self.school.name),
            "clock": self.clock_view(),
            "date": day["date"],
            "city_aqi": day["city_aqi"],
            "indicative_grap": day["indicative_grap"],
            "official_grap": meta.get("official_grap_stage"),
            "grap_stage": day["grap_stage"],
            "grap": {
                "name_en": stage.name_en,
                "name_hi": stage.name_hi,
                "reminder_en": stage.school_reminder_en,
                "reminder_hi": stage.school_reminder_hi,
                "circulars_url": grap.DOE_CIRCULARS_URL,
            },
            "decisions": day["decisions"],
            "policies": {
                pid: {"en": POLICIES[pid].en, "hi": POLICIES[pid].hi, "source": POLICIES[pid].source}
                for d in day["decisions"]
                for pid in d["policy_ids"]
                if pid in POLICIES
            },
            "hourly": day["hourly"],
            "forecast_source": day["forecast_source"],
            "rooms": rooms,
            "simulated": day["simulated"],
        }

    # ── principal actions (Cedar-checked, always logged) ─────────────────────────────────────────────
    def override(self, key: str, outdoor: bool, reason: str, user_id: str) -> Item:
        """Override one of today's activity decisions. Only a principal may (Cedar A2/A3); every override
        is written to the audit log with who, when and why, and the affected rooms are re-planned."""
        authorize = getattr(self.policy, "authorize", None)
        if authorize is not None:
            d = authorize(user_id, "plan.override", "School", self.school.school_id)
            if not d.allowed:
                raise PermissionError(f"Only a principal can override decisions ({', '.join(d.policy_ids)})")
        reason = reason.strip()
        if not reason:
            raise ValueError("Give a reason; overrides are logged")
        day = self.day()
        decision = next((x for x in day["decisions"] if x["key"] == key), None)
        if decision is None:
            raise KeyError(key)
        now = self.clock.now()
        decision.update(
            override=bool(outdoor),
            override_by=user_id,
            override_reason=reason[:200],
            override_at=hhmm(int(ist_minute(now))),
        )
        self.store.put(f"SCHOOL#{self.school.school_id}", f"DAY#{day['date']}", day)
        self._day_cache[day["date"]] = (time.monotonic(), day)
        entry = {
            "at": now,
            "time": hhmm(int(ist_minute(now))),
            "date": day["date"],
            "by": user_id,
            "key": key,
            "label": decision["label"],
            "outdoor": bool(outdoor),
            "was_outdoor": decision["outdoor"],
            "policy_ids": decision["policy_ids"],
            "reason": reason[:200],
        }
        self.store.put(f"AUDIT#{self.school.school_id}", f"{iso(now)}#{key}", entry)
        rooms = [key.split(":")[1]] if key.startswith("pe:") else [r.room_id for r in self.school.rooms]
        for rid in rooms:
            self.replan(rid, reason=f"override {key}")
        return entry

    def audit(self, limit: int = 20) -> list[Item]:
        return self.store.query(f"AUDIT#{self.school.school_id}", "", limit=limit, newest_first=True)

    # ── demo support ─────────────────────────────────────────────────────────────────────────────────
    def reset(self) -> None:
        if hasattr(self.store, "clear"):
            self.store.clear()
        self._forecast_cache.clear()
        self.seed()


def window_index(w: str) -> int:
    return WINDOW_ORDER.index(Window(w))


__all__ = ["IST", "Engine", "WindowGuess", "ist_epoch", "window_index"]
