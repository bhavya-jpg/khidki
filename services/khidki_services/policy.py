"""Policy interface. Cedar (Phase 3) implements it; `PermitAll` is the explicit placeholder until then."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from khidki_core.optimizer import N_CO2_BANDS, BoolArray
from khidki_core.physics import ActionArrays, DriveSeries
from khidki_services.seed import SchoolConfig


@dataclass(frozen=True)
class Decision:
    allowed: bool
    policy_ids: tuple[str, ...] = field(default_factory=tuple)
    """Policies that decided it (forbids that fired, or the permit)."""


@dataclass(frozen=True)
class ActivityContext:
    kind: str  # "assembly" | "pe" | "recess_outdoor"
    max_pm25_during: float
    grap_stage: int
    min_grade: int


class PolicyEngine(Protocol):
    def ventilation_mask(self, drive: DriveSeries, aa: ActionArrays, grap_stage: int) -> BoolArray: ...

    def activity(self, ctx: ActivityContext) -> Decision: ...


class PermitAll:
    """No policy: every action and activity allowed. Used only before Cedar is wired in."""

    def ventilation_mask(self, drive: DriveSeries, aa: ActionArrays, grap_stage: int) -> BoolArray:
        return np.ones((len(drive), N_CO2_BANDS, len(aa)), dtype=np.bool_)

    def activity(self, ctx: ActivityContext) -> Decision:
        return Decision(allowed=True, policy_ids=("default-permit",))


class CedarPolicyEngine:
    """The real policy engine: Cedar decides ventilation masks and activity decisions."""

    def __init__(self, school: SchoolConfig) -> None:
        from khidki_core.policy import CedarPolicy

        rooms = {
            r.room_id: {
                "grade": r.grade,
                "sensitive_count": r.sensitive_count,
                "has_purifier": r.params.has_purifier,
            }
            for r in school.rooms
        }
        users: dict[str, dict[str, object]] = {"principal": {"role": "principal"}}
        for r in school.rooms:
            users[f"teacher-{r.room_id}"] = {"role": "teacher", "room": r.room_id}
            users[f"parent-{r.room_id}"] = {"role": "parent", "room": r.room_id}
        self.cedar = CedarPolicy(school_id=school.school_id, rooms=rooms, users=users)

    def ventilation_mask(self, drive: DriveSeries, aa: ActionArrays, grap_stage: int) -> BoolArray:
        return self.cedar.ventilation_mask(drive, aa, grap_stage)

    def activity(self, ctx: ActivityContext) -> Decision:
        d = self.cedar.activity_decision(ctx.kind, ctx.max_pm25_during, ctx.grap_stage, ctx.min_grade)
        return Decision(allowed=d.allowed, policy_ids=d.policy_ids)

    def authorize(self, user_id: str, action: str, resource_type: str, resource_id: str) -> Decision:
        d = self.cedar.authorize(user_id, action, resource_type, resource_id)
        return Decision(allowed=d.allowed, policy_ids=d.policy_ids)
