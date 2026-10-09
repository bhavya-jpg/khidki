"""Policy as code with Cedar (an AWS open-source project), via cedarpy.

Code and Cedar decide what is allowed; the language model only explains. Every decision returns the policy
ids that decided it, so the UI and the agent can say "PE moved indoors because of S2: 142 > 90".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import cedarpy
import numpy as np
from numpy.typing import NDArray

from khidki_core.optimizer import N_CO2_BANDS
from khidki_core.physics import ActionArrays, DriveSeries
from khidki_core.schemas import Window

HERE = Path(__file__).parent
POLICY_TEXT = (HERE / "khidki.cedar").read_text()
SCHEMA_TEXT = (HERE / "khidki.cedarschema").read_text()

VENT_ACTION = {
    Window.CLOSED: "ventilate.close",
    Window.CRACKED: "ventilate.crack",
    Window.OPEN_ONE: "ventilate.open",
    Window.OPEN_BOTH: "ventilate.open",
}


@dataclass(frozen=True)
class PolicyInfo:
    id: str
    en: str
    hi: str
    source: str


def parse_policies(text: str = POLICY_TEXT) -> dict[str, PolicyInfo]:
    """Read @id/@en/@hi annotations so every decision can be explained in both languages."""
    out: dict[str, PolicyInfo] = {}
    for block in re.split(r"\n(?=@id\()", text):
        m = re.search(r'@id\("([^"]+)"\)', block)
        if not m:
            continue
        en = re.search(r'@en\("([^"]*)"\)', block)
        hi = re.search(r'@hi\("([^"]*)"\)', block)
        body = "\n".join(
            line
            for line in block.splitlines()
            if line.strip() and not line.startswith("@") and not line.startswith("//")
        )
        out[m.group(1)] = PolicyInfo(
            m.group(1), en.group(1) if en else "", hi.group(1) if hi else "", body.strip()
        )
    return out


POLICIES = parse_policies()


def validate() -> tuple[bool, list[str]]:
    res = cedarpy.validate_policies(POLICY_TEXT, SCHEMA_TEXT)
    return bool(res.validation_passed), [str(e) for e in res.errors]


@dataclass(frozen=True)
class CedarDecision:
    allowed: bool
    policy_ids: tuple[str, ...]


def _uid(t: str, i: str) -> dict[str, str]:
    return {"type": f"Khidki::{t}", "id": i}


@dataclass
class CedarPolicy:
    """Implements the services' PolicyEngine protocol."""

    school_id: str = "dsv"
    rooms: dict[str, dict[str, Any]] = field(default_factory=dict)
    """room_id -> {"grade", "sensitive_count", "has_purifier"}"""
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    """user_id -> {"role", "room" (optional)}"""

    _vent_cache: dict[tuple[int, int, int, int, str], bool] = field(default_factory=dict, repr=False)

    @cached_property
    def _policies(self) -> cedarpy.PolicySet:
        return cedarpy.PolicySet.from_str(POLICY_TEXT)

    @cached_property
    def _schema(self) -> cedarpy.Schema:
        return cedarpy.Schema.from_str(SCHEMA_TEXT)

    @cached_property
    def _entities(self) -> cedarpy.Entities:
        school = _uid("School", self.school_id)
        ents: list[dict[str, Any]] = [{"uid": school, "attrs": {"name": self.school_id}, "parents": []}]
        for rid, r in self.rooms.items():
            ents.append(
                {
                    "uid": _uid("Room", rid),
                    "parents": [school],
                    "attrs": {
                        "grade": int(r["grade"]),
                        "sensitiveCount": int(r.get("sensitive_count", 0)),
                        "hasPurifier": bool(r.get("has_purifier", False)),
                    },
                }
            )
        for uid, u in self.users.items():
            parents = [school] + ([_uid("Room", u["room"])] if u.get("room") else [])
            ents.append(
                {
                    "uid": _uid("User", uid),
                    "parents": parents,
                    "attrs": {"role": u["role"], "school": {"__entity": school}},
                }
            )
        for kind in ("assembly", "pe", "recess_outdoor"):
            ents.append({"uid": _uid("Activity", kind), "parents": [school], "attrs": {"kind": kind}})
        import json

        return cedarpy.Entities.from_json_str(json.dumps(ents))

    def _decide(self, requests: list[dict[str, Any]]) -> list[CedarDecision]:
        results = cedarpy.is_authorized_batch(requests, self._policies, self._entities, self._schema)
        out = []
        for r in results:
            if r.diagnostics.errors:
                raise RuntimeError(f"Cedar evaluation error: {r.diagnostics.errors}")
            ids = (
                tuple(sorted(r.diagnostics.id_annotations_by_reason.values()))
                if hasattr(r.diagnostics, "id_annotations_by_reason")
                else tuple(r.diagnostics.reasons)
            )
            out.append(CedarDecision(allowed=bool(r.allowed), policy_ids=ids))
        return out

    # ── ventilation ───────────────────────────────────────────────────────────────────────────────
    def ventilation_mask(
        self, drive: DriveSeries, aa: ActionArrays, grap_stage: int, room_id: str | None = None
    ) -> NDArray[np.bool_]:
        """allowed[t, co2_band, action]. Identical contexts are asked once (batched)."""
        room = room_id or next(iter(self.rooms), "room")
        kinds = sorted({VENT_ACTION[a.window] for a in aa.actions})
        keys: dict[tuple[int, int, int, int, str], int] = {}
        requests: list[dict[str, Any]] = []
        index = np.empty((len(drive), N_CO2_BANDS, len(kinds)), dtype=np.int64)
        for t in range(len(drive)):
            pm, temp, minute = (
                round(float(drive.pm_out[t])),
                round(float(drive.temp_out[t])),
                int(drive.t_min[t]),
            )
            for band in range(N_CO2_BANDS):
                for k, kind in enumerate(kinds):
                    # minute and temperature are in the context for future policies; none use them yet,
                    # so they're left out of the cache key's precision only through rounding.
                    key = (pm, band, grap_stage, temp, kind)
                    if key not in keys:
                        keys[key] = len(requests)
                        requests.append(
                            {
                                "principal": _uid("Room", room),
                                "resource": _uid("Room", room),
                                "action": {"type": "Khidki::Action", "id": kind},
                                "context": {
                                    "outdoorPm25": pm,
                                    "co2Band": band,
                                    "grapStage": grap_stage,
                                    "minuteOfDay": minute,
                                    "tempOutC": temp,
                                },
                            }
                        )
                    index[t, band, k] = keys[key]
        # Contexts repeat across re-plans (inputs are rounded), so remember decisions.
        key_list = list(keys)
        missing = [i for i, k in enumerate(key_list) if k not in self._vent_cache]
        if missing:
            for i, d in zip(missing, self._decide([requests[i] for i in missing]), strict=True):
                self._vent_cache[key_list[i]] = d.allowed
        allowed_req = np.array([self._vent_cache[k] for k in key_list], dtype=np.bool_)
        out = np.ones((len(drive), N_CO2_BANDS, len(aa)), dtype=np.bool_)
        for a, act in enumerate(aa.actions):
            out[:, :, a] = allowed_req[index[:, :, kinds.index(VENT_ACTION[act.window])]]
        return out

    def ventilation(
        self,
        window: Window,
        outdoor_pm25: float,
        co2_band: int,
        grap_stage: int,
        room_id: str | None = None,
        minute: int = 600,
        temp_c: float = 20,
    ) -> CedarDecision:
        room = room_id or next(iter(self.rooms), "room")
        return self._decide(
            [
                {
                    "principal": _uid("Room", room),
                    "resource": _uid("Room", room),
                    "action": {"type": "Khidki::Action", "id": VENT_ACTION[window]},
                    "context": {
                        "outdoorPm25": round(outdoor_pm25),
                        "co2Band": co2_band,
                        "grapStage": grap_stage,
                        "minuteOfDay": minute,
                        "tempOutC": round(temp_c),
                    },
                }
            ]
        )[0]

    # ── activities ────────────────────────────────────────────────────────────────────────────────
    def activity_decision(
        self, kind: str, max_pm25_during: float, grap_stage: int, min_grade: int
    ) -> CedarDecision:
        return self._decide(
            [
                {
                    "principal": _uid("School", self.school_id),
                    "resource": _uid("Activity", kind),
                    "action": {"type": "Khidki::Action", "id": "activity.outdoor"},
                    "context": {
                        "maxPm25During": round(max_pm25_during),
                        "grapStage": grap_stage,
                        "minGrade": min_grade,
                    },
                }
            ]
        )[0]

    # ── access ────────────────────────────────────────────────────────────────────────────────────
    def authorize(self, user_id: str, action: str, resource_type: str, resource_id: str) -> CedarDecision:
        return self._decide(
            [
                {
                    "principal": _uid("User", user_id),
                    "action": {"type": "Khidki::Action", "id": action},
                    "resource": _uid(resource_type, resource_id),
                    "context": {},
                }
            ]
        )[0]
