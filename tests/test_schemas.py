"""Schema validation tests — no API calls. Prove the data contracts fail loudly."""

import pytest
from pydantic import ValidationError

from src.schemas.critique import CritiqueReport, Issue, Severity
from src.schemas.verdict import Verdict


def _valid_issue():
    return Issue(quote="the moon is made of cheese", problem="false claim", severity=Severity.HIGH)


def test_valid_critique_report():
    r = CritiqueReport(
        dimension="accuracy",
        score=4,
        issues=[_valid_issue()],
        confidence=0.9,
        critic_model="gpt-4o",
    )
    assert r.score == 4
    assert r.issues[0].severity is Severity.HIGH


def test_score_out_of_range_rejected():
    for bad in (0, 6, -1):
        with pytest.raises(ValidationError):
            CritiqueReport(dimension="logic", score=bad, issues=[], confidence=0.5, critic_model="x")


def test_confidence_out_of_range_rejected():
    for bad in (-0.1, 1.5):
        with pytest.raises(ValidationError):
            CritiqueReport(dimension="logic", score=3, issues=[], confidence=bad, critic_model="x")


def test_invalid_dimension_rejected():
    with pytest.raises(ValidationError):
        CritiqueReport(dimension="vibes", score=3, issues=[], confidence=0.5, critic_model="x")


def test_invalid_severity_rejected():
    with pytest.raises(ValidationError):
        Issue(quote="q", problem="p", severity="catastrophic")


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        CritiqueReport(dimension="accuracy", issues=[], confidence=0.5, critic_model="x")  # no score


def test_verdict_overall_score_range():
    for bad in (0, 11):
        with pytest.raises(ValidationError):
            Verdict(
                overall_score=bad,
                confidence=0.5,
                summary="s",
                adjudicated=True,
            )


def test_unwraps_single_key_envelope_from_local_model():
    # llama3 in JSON mode sometimes wraps the object under its class name.
    wrapped = {
        "CritiqueReport": {
            "dimension": "accuracy",
            "score": 3,
            "issues": [],
            "confidence": 0.6,
            "critic_model": "llama3",
        }
    }
    r = CritiqueReport.model_validate(wrapped)
    assert r.dimension == "accuracy"
    assert r.score == 3


def test_minimal_valid_verdict():
    v = Verdict(overall_score=8, confidence=0.7, summary="looks good", adjudicated=False)
    assert v.confirmed_issues == []
    assert v.dismissed_flags == []
    assert v.adjudicated is False
