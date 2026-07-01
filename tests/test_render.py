"""Tests for the UI's quote-highlighting logic (no Streamlit / browser needed)."""

from src.schemas.critique import CritiqueReport, Issue, Severity
from ui.render import esc, highlight_output


def _report(dim, *issues):
    return CritiqueReport(
        dimension=dim, score=3, issues=list(issues), confidence=0.8, critic_model="m"
    )


def test_quote_is_wrapped_with_span():
    text = "Mars has three moons including Triton."
    reports = [_report("accuracy", Issue(quote="Triton", problem="wrong planet", severity=Severity.HIGH))]
    html = highlight_output(text, reports)
    assert "<span" in html
    assert "Triton" in html
    assert "wrong planet" in html  # tooltip text present


def test_missing_quote_is_skipped_not_crashed():
    text = "A clean sentence."
    reports = [_report("logic", Issue(quote="not in text", problem="x", severity=Severity.LOW))]
    html = highlight_output(text, reports)
    assert "<span" not in html
    assert "A clean sentence." in html


def test_overlapping_quotes_do_not_double_wrap():
    text = "the atmosphere is oxygen-rich and breathable"
    reports = [
        _report("accuracy", Issue(quote="oxygen-rich and breathable", problem="false", severity=Severity.HIGH)),
        _report("logic", Issue(quote="breathable", problem="leap", severity=Severity.MEDIUM)),
    ]
    html = highlight_output(text, reports)
    # The longer span wins; we must not produce nested/overlapping spans.
    assert html.count("</span>") == 1


def test_html_is_escaped():
    text = "value < 5 and x > 3 & y"
    html = highlight_output(text, [])
    assert "&lt;" in html and "&gt;" in html and "&amp;" in html
    assert "<5" not in html  # raw angle brackets must not leak through


def test_no_reports_returns_escaped_plaintext():
    assert highlight_output("plain", None) == "plain"
    assert esc("<b>") == "&lt;b&gt;"
