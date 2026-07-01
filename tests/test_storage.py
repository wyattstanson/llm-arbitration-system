"""SQLite audit-trail tests — no API calls. Uses an isolated temp DB per test."""

import pytest

from src.schemas.critique import CritiqueReport, Issue, Severity
from src.schemas.verdict import ConfirmedIssue, Disagreement, DismissedFlag, Verdict
from src.storage import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ARBITRATION_DB_PATH", str(tmp_path / "test.db"))
    yield


def _rich_verdict() -> Verdict:
    """A verdict exercising every nested field, so the round-trip is meaningful."""
    return Verdict(
        overall_score=4,
        confidence=0.62,
        confirmed_issues=[
            ConfirmedIssue(
                description="Triton is a moon of Neptune, not Mars.",
                severity=Severity.HIGH,
                evidence="Verified against astronomical fact.",
                source_critics=["accuracy", "logic"],
            )
        ],
        dismissed_flags=[
            DismissedFlag(
                description="Output too detailed for a 'quick' briefing.",
                raised_by="completeness",
                reasoning="It still addresses the request; the concern is overstated.",
            )
        ],
        summary="Multiple factual errors confirmed; one weak flag dismissed.",
        critic_reports=[
            CritiqueReport(
                dimension="accuracy",
                score=2,
                issues=[Issue(quote="Triton", problem="wrong planet", severity=Severity.HIGH)],
                confidence=0.9,
                critic_model="llama3",
            )
        ],
        disagreements=[
            Disagreement(
                type="presence_mismatch",
                description="accuracy flagged what others missed",
                critics_involved=["accuracy", "logic", "completeness"],
                details="only accuracy caught the Triton error",
            )
        ],
        adjudicated=True,
    )


def test_round_trip_identical_content():
    verdict = _rich_verdict()
    rec = db.save_arbitration("Mars output text", "Brief me on Mars", verdict)

    fetched = db.get_arbitration(rec.id)
    assert fetched is not None
    # The whole record must come back byte-for-byte identical after a DB round-trip.
    assert fetched.model_dump() == rec.model_dump()
    assert fetched.verdict == verdict


def test_get_missing_returns_none():
    assert db.get_arbitration("does-not-exist") is None


def test_list_orders_newest_first():
    v = _rich_verdict()
    r1 = db.save_arbitration("first", None, v, created_at="2026-01-01T00:00:00+00:00")
    r2 = db.save_arbitration("second", None, v, created_at="2026-06-01T00:00:00+00:00")
    ids = [r.id for r in db.list_arbitrations()]
    assert ids.index(r2.id) < ids.index(r1.id)


def test_each_save_gets_unique_id():
    v = _rich_verdict()
    a = db.save_arbitration("x", None, v)
    b = db.save_arbitration("x", None, v)
    assert a.id != b.id
