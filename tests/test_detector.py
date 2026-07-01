"""Disagreement detector tests — synthetic CritiqueReports, zero live calls."""

from src.disagreement.detector import detect_disagreements
from src.schemas.critique import CritiqueReport, Issue, Severity


def report(dimension, score, issues, confidence=0.9, model="test"):
    return CritiqueReport(
        dimension=dimension,
        score=score,
        issues=issues,
        confidence=confidence,
        critic_model=model,
    )


def issue(quote, problem="problem", severity=Severity.MEDIUM):
    return Issue(quote=quote, problem=problem, severity=severity)


# --- severity_gap ------------------------------------------------------------
def test_severity_gap_low_vs_high_same_region():
    quote = "the company will grow 11x next quarter"
    reports = [
        report("accuracy", 3, [issue(quote, "overstated", Severity.LOW)]),
        report("logic", 2, [issue(quote, "unsupported leap", Severity.HIGH)]),
        report("completeness", 5, []),
    ]
    types = [d.type for d in detect_disagreements(reports)]
    assert "severity_gap" in types


def test_no_severity_gap_when_only_two_levels_apart():
    quote = "the company will grow 11x next quarter"
    reports = [
        report("accuracy", 3, [issue(quote, "x", Severity.MEDIUM)]),  # rank 3
        report("logic", 3, [issue(quote, "y", Severity.HIGH)]),       # rank 5, gap = 2 (not > 2)
        report("completeness", 5, []),
    ]
    assert all(d.type != "severity_gap" for d in detect_disagreements(reports))


# --- presence_mismatch -------------------------------------------------------
def test_presence_mismatch_when_others_score_high():
    reports = [
        report("accuracy", 2, [issue("Triton is a moon of Mars", "false", Severity.HIGH)]),
        report("logic", 5, []),         # confident-clean
        report("completeness", 4, []),  # confident-clean
    ]
    types = [d.type for d in detect_disagreements(reports)]
    assert "presence_mismatch" in types
    assert "unique_find" not in types  # high-score condition routes it to presence_mismatch


# --- unique_find -------------------------------------------------------------
def test_unique_find_when_others_not_confident():
    reports = [
        report("logic", 2, [issue("therefore profits triple", "non-sequitur", Severity.HIGH)]),
        report("accuracy", 3, []),       # not >= 4 -> not "confident clean"
        report("completeness", 3, []),
    ]
    types = [d.type for d in detect_disagreements(reports)]
    assert "unique_find" in types
    assert "presence_mismatch" not in types


# --- agreement = no disagreement --------------------------------------------
def test_agreement_same_region_close_severity_is_not_flagged():
    quote = "humans could breathe the martian air unaided"
    reports = [
        report("accuracy", 2, [issue(quote, "false", Severity.HIGH)]),
        report("logic", 2, [issue(quote, "unjustified", Severity.HIGH)]),  # same region, same sev
        report("completeness", 5, []),
    ]
    # Same region + identical severity -> not a severity_gap, and not unique (two critics caught it).
    assert detect_disagreements(reports) == []


def test_clean_reports_produce_no_disagreements():
    reports = [
        report("accuracy", 5, []),
        report("logic", 5, []),
        report("completeness", 5, []),
    ]
    assert detect_disagreements(reports) == []


def test_handles_missing_critic_gracefully():
    # One critic failed (None) — detector should still work on the rest.
    reports = [
        report("accuracy", 2, [issue("Triton is a moon of Mars", "false", Severity.HIGH)]),
        None,
        report("completeness", 4, []),
    ]
    result = detect_disagreements(reports)
    # accuracy's catch is unique among the present critics; completeness scored 4 -> presence_mismatch
    assert any(d.type == "presence_mismatch" for d in result)
