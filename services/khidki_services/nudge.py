"""The nudge-and-verify state machine (NudgeSM), as pure functions.

Local mode runs it from a tick loop; in AWS the same transitions are a Step Functions state machine with a
`waitForTaskToken` callback for the teacher's tap. Both are tested against this file.

    ISSUED ──ack "done"──────────► VERIFYING ──wait 3 sim-min──► verify from the CO₂ curve
       │──ack "can't" (reason) ──► NOT_POSSIBLE (+ constraint, re-plan)
       └──no tap in 3 sim-min ──► VERIFYING (no_ack)

    verify: matches         ──► VERIFIED (or VERIFIED_SILENT if nobody tapped)
            mismatch, try 1 ──► FOLLOW_UP ("only one side seems open?" / gentle re-nudge) ──► same loop once
            otherwise       ──► NOT_FOLLOWED or PARTIAL (re-plan; never shown as blame)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from khidki_core.inference import Verdict

ACK_TIMEOUT_S = 180.0
# The fit needs six readings and sensors report every 30 s. A 3-minute wait gave five or six depending on
# when the tap landed, so about half the checks came back "inconclusive" and fell back to trusting the tap.
VERIFY_WAIT_S = 240.0


class Status(StrEnum):
    ISSUED = "issued"
    VERIFYING = "verifying"
    FOLLOW_UP = "follow_up"
    DONE = "done"


class Outcome(StrEnum):
    VERIFIED = "verified"
    VERIFIED_SILENT = "verified_silent"
    PARTIAL = "partial"
    NOT_FOLLOWED = "not_followed"
    NOT_POSSIBLE = "not_possible"


class FollowUp(StrEnum):
    OTHER_SIDE = "other_side"
    NOT_CHANGED = "not_changed"
    GENTLE = "gentle"


class Effect(StrEnum):
    RECORD_CONSTRAINT = "record_constraint"
    REPLAN = "replan"
    VERIFY_NOW = "verify_now"


@dataclass(frozen=True)
class NudgeState:
    status: Status = Status.ISSUED
    attempt: int = 1
    ack: str | None = None  # "done" | "cant" | "no_ack"
    cant_reason: str | None = None
    deadline: float = 0.0
    """When to stop waiting for a tap (ISSUED / FOLLOW_UP) or when to verify (VERIFYING)."""
    follow_up: FollowUp | None = None
    outcome: Outcome | None = None
    verify_from: float = 0.0
    """Telemetry after this time is evidence."""
    verifiable: bool = True
    """False for purifier-only instructions: CO₂ can't confirm them, the teacher's tap does."""
    history: tuple[str, ...] = field(default_factory=tuple)


def issue(now: float, verifiable: bool = True) -> NudgeState:
    return NudgeState(deadline=now + ACK_TIMEOUT_S, verifiable=verifiable, history=("issued",))


def on_ack(
    s: NudgeState, now: float, result: str, reason: str | None = None
) -> tuple[NudgeState, list[Effect]]:
    if s.status not in (Status.ISSUED, Status.FOLLOW_UP):
        return s, []
    if result == "cant":
        done = replace(
            s,
            status=Status.DONE,
            ack="cant",
            cant_reason=reason,
            outcome=Outcome.NOT_POSSIBLE,
            history=(*s.history, f"cant:{reason}"),
        )
        return done, [Effect.RECORD_CONSTRAINT, Effect.REPLAN]
    if not s.verifiable:
        return replace(
            s, status=Status.DONE, ack="done", outcome=Outcome.VERIFIED, history=(*s.history, "done")
        ), []
    return replace(
        s,
        status=Status.VERIFYING,
        ack="done",
        deadline=now + VERIFY_WAIT_S,
        verify_from=now + 20,
        history=(*s.history, "done"),
    ), []


def on_tick(s: NudgeState, now: float) -> tuple[NudgeState, list[Effect]]:
    """Time passing: a tap timeout, or verification falling due."""
    if s.status in (Status.ISSUED, Status.FOLLOW_UP) and now >= s.deadline:
        if not s.verifiable:
            return replace(
                s,
                status=Status.DONE,
                ack="no_ack",
                outcome=Outcome.NOT_FOLLOWED,
                history=(*s.history, "no_ack"),
            ), [Effect.REPLAN]
        ack = s.ack if s.status == Status.FOLLOW_UP and s.ack == "done" else "no_ack"
        return replace(
            s,
            status=Status.VERIFYING,
            ack=ack,
            deadline=now + VERIFY_WAIT_S,
            verify_from=now - ACK_TIMEOUT_S + 30,
            history=(*s.history, "no_ack"),
        ), []
    if s.status == Status.VERIFYING and now >= s.deadline:
        return s, [Effect.VERIFY_NOW]
    return s, []


def on_verdict(s: NudgeState, now: float, verdict: Verdict) -> tuple[NudgeState, list[Effect]]:
    if s.status != Status.VERIFYING:
        return s, []
    h = (*s.history, f"verdict:{verdict.value}")
    if verdict == Verdict.VERIFIED:
        outcome = Outcome.VERIFIED if s.ack == "done" else Outcome.VERIFIED_SILENT
        return replace(s, status=Status.DONE, outcome=outcome, history=h), []
    if s.attempt == 1:
        if s.ack == "done":
            fu = FollowUp.OTHER_SIDE if verdict == Verdict.PARTIAL else FollowUp.NOT_CHANGED
        else:
            fu = FollowUp.GENTLE
        return replace(
            s, status=Status.FOLLOW_UP, attempt=2, follow_up=fu, deadline=now + ACK_TIMEOUT_S, history=h
        ), []
    outcome = Outcome.PARTIAL if verdict == Verdict.PARTIAL else Outcome.NOT_FOLLOWED
    return replace(s, status=Status.DONE, outcome=outcome, history=h), [Effect.REPLAN]
