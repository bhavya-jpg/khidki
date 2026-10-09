"""Policy interface. Cedar (Phase 3) implements it; `PermitAll` is the explicit placeholder until then."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from khidki_core.optimizer import N_CO2_BANDS, BoolArray
from khidki_core.physics import ActionArrays, DriveSeries


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
