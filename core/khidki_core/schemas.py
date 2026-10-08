"""Typed domain models shared by core, services, the API and the web app.

Units are in field names or docstrings: ppm, µg/m³, h⁻¹ (air changes per hour), m³, minutes of day (IST).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Window(StrEnum):
    """Window states, ordered from least to most open."""

    CLOSED = "closed"
    CRACKED = "cracked"
    OPEN_ONE = "open_one"
    OPEN_BOTH = "open_both"


WINDOW_ORDER: tuple[Window, ...] = tuple(Window)


class Purifier(StrEnum):
    OFF = "off"
    ON = "on"


class Profile(StrEnum):
    BALANCED = "balanced"
    LUNGS_FIRST = "lungs_first"
    FOCUS_FIRST = "focus_first"


PROFILE_ALPHA: dict[Profile, float] = {
    Profile.BALANCED: 0.5,
    Profile.LUNGS_FIRST: 0.7,
    Profile.FOCUS_FIRST: 0.35,
}


class ReasonCode(StrEnum):
    """Why the plan does something. The UI and agent turn these into fixed bilingual text."""

    CO2_RISING_FAST = "CO2_RISING_FAST"
    OUTDOOR_PM_LOW_WINDOW = "OUTDOOR_PM_LOW_WINDOW"
    RECESS_PURGE = "RECESS_PURGE"
    OUTDOOR_PM_SPIKE_CLOSE = "OUTDOOR_PM_SPIKE_CLOSE"
    PURIFIER_DURING_CLOSED = "PURIFIER_DURING_CLOSED"
    AIR_REFRESHED = "AIR_REFRESHED"
    COLD_LIMIT = "COLD_LIMIT"
    POLICY_FORBIDS_OPEN = "POLICY_FORBIDS_OPEN"
    ATTENTION_BUDGET = "ATTENTION_BUDGET"
    KEEP_STEADY = "KEEP_STEADY"


class Action(BaseModel):
    model_config = ConfigDict(frozen=True)

    window: Window
    purifier: Purifier = Purifier.OFF


def _default_lambda() -> dict[Window, float]:
    return {Window.CLOSED: 0.7, Window.CRACKED: 2.5, Window.OPEN_ONE: 6.0, Window.OPEN_BOTH: 10.0}


def _default_penetration() -> dict[Window, float]:
    return {Window.CLOSED: 0.8, Window.CRACKED: 0.95, Window.OPEN_ONE: 1.0, Window.OPEN_BOTH: 1.0}


def _default_open_fraction() -> dict[Window, float]:
    return {Window.CLOSED: 0.0, Window.CRACKED: 0.3, Window.OPEN_ONE: 0.6, Window.OPEN_BOTH: 1.0}


class RoomParams(BaseModel):
    """Physical parameters of one classroom. Defaults are literature-based (docs/physics.md) until the
    nightly fingerprint replaces them."""

    model_config = ConfigDict(frozen=True)

    volume_m3: float = Field(166.0, gt=0)
    students: int = Field(44, ge=0)
    adults: int = Field(1, ge=0)
    has_purifier: bool = False
    lam: dict[Window, float] = Field(default_factory=_default_lambda)
    """Air changes per hour by window state."""
    pen: dict[Window, float] = Field(default_factory=_default_penetration)
    """PM2.5 penetration factor by window state."""
    open_fraction: dict[Window, float] = Field(default_factory=_default_open_fraction)
    """How open the room is to cold outdoor air (0..1), for the cold-exposure proxy."""
    deposition_per_h: float = Field(0.2, ge=0)
    purifier_cadr_m3_h: float = Field(350.0, ge=0)
    purifier_effectiveness: float = Field(0.8, ge=0, le=1)
    indoor_pm_source_ug_h: float = Field(0.0, ge=0)
    gen_child_lps: float = 0.0035
    """CO₂ generation per seated 10 to 13 year old, L/s (after Persily and de Jonge 2017)."""
    gen_adult_lps: float = 0.0052


class Constraint(BaseModel):
    """A teacher's "can't right now" reason, turned into a planning constraint."""

    model_config = ConfigDict(frozen=True)

    kind: str = Field(pattern="^(cold|noise|rain|exam)$")
    start_min: int = Field(ge=0, le=24 * 60)
    end_min: int = Field(ge=0, le=24 * 60)
    window_at_start: Window = Window.CLOSED
    """Window state when the constraint was recorded (used to freeze the window during an exam)."""


class Kpis(BaseModel):
    pm_dose_ug: float
    """PM2.5 inhaled per child while in the room, µg."""
    co2_min_over_1000: float
    co2_min_over_1500: float
    co2_points: float
    cold_deg_min: float
    window_changes: int
    mean_pm_occupied: float
    max_co2: float


class PlanStep(BaseModel):
    t_min: int
    t: str
    window: Window
    purifier: Purifier
    predicted_co2: float
    predicted_pm: float
    occupied: bool
    reason_code: ReasonCode


class Instruction(BaseModel):
    t_start_min: int
    t_end_min: int
    t_start: str
    action: Action
    duration_min: int
    reason_code: ReasonCode


class Plan(BaseModel):
    room_id: str
    date: str
    version: int = 1
    profile: Profile
    mu: float
    """Switch penalty the attention-budget bisection settled on."""
    budget_binding: bool
    steps: list[PlanStep]
    instructions: list[Instruction]
    kpis_predicted: Kpis
    baselines_predicted: dict[str, Kpis]
    constraints: list[Constraint] = Field(default_factory=list)
    simulated: bool = True
