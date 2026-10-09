"""NudgeSM branches (docs/SPEC.md §8.4), as pure transitions. The Step Functions definition mirrors these."""

from khidki_core.inference import Verdict
from khidki_services import nudge as n


def test_done_and_match_is_verified() -> None:
    s = n.issue(0)
    s, fx = n.on_ack(s, 30, "done")
    assert s.status == n.Status.VERIFYING and fx == []
    s, fx = n.on_tick(s, 30 + n.VERIFY_WAIT_S)
    assert fx == [n.Effect.VERIFY_NOW]
    s, fx = n.on_verdict(s, 220, Verdict.VERIFIED)
    assert s.status == n.Status.DONE and s.outcome == n.Outcome.VERIFIED and fx == []


def test_done_but_partial_asks_for_other_side_then_verifies() -> None:
    s, _ = n.on_ack(n.issue(0), 30, "done")
    s, _ = n.on_verdict(s, 220, Verdict.PARTIAL)
    assert s.status == n.Status.FOLLOW_UP and s.follow_up == n.FollowUp.OTHER_SIDE and s.attempt == 2
    s, _ = n.on_ack(s, 260, "done")
    s, _ = n.on_verdict(s, 450, Verdict.VERIFIED)
    assert s.outcome == n.Outcome.VERIFIED


def test_no_ack_but_air_changed_is_verified_silently() -> None:
    s, _ = n.on_tick(n.issue(0), n.ACK_TIMEOUT_S)
    assert s.status == n.Status.VERIFYING and s.ack == "no_ack"
    s, _ = n.on_verdict(s, 400, Verdict.VERIFIED)
    assert s.outcome == n.Outcome.VERIFIED_SILENT


def test_no_ack_and_no_change_renudges_once_then_replans() -> None:
    s, _ = n.on_tick(n.issue(0), n.ACK_TIMEOUT_S)
    s, _ = n.on_verdict(s, 400, Verdict.NOT_CHANGED)
    assert s.status == n.Status.FOLLOW_UP and s.follow_up == n.FollowUp.GENTLE
    s, _ = n.on_tick(s, 400 + n.ACK_TIMEOUT_S)
    s, fx = n.on_verdict(s, 800, Verdict.NOT_CHANGED)
    assert s.outcome == n.Outcome.NOT_FOLLOWED and fx == [n.Effect.REPLAN]


def test_cant_records_constraint_and_replans() -> None:
    s, fx = n.on_ack(n.issue(0), 20, "cant", "cold")
    assert s.outcome == n.Outcome.NOT_POSSIBLE and s.cant_reason == "cold"
    assert fx == [n.Effect.RECORD_CONSTRAINT, n.Effect.REPLAN]


def test_purifier_only_trusts_the_tap() -> None:
    s, _ = n.on_ack(n.issue(0, verifiable=False), 20, "done")
    assert s.outcome == n.Outcome.VERIFIED


def test_late_ack_after_done_is_ignored() -> None:
    s, _ = n.on_ack(n.issue(0), 20, "cant", "rain")
    s2, fx = n.on_ack(s, 40, "done")
    assert s2 == s and fx == []
