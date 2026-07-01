"""Graph orchestration tests — critics are mocked, so these run fast with no API calls.

Covers the Phase 2 definition-of-done items that don't need live models:
  - unanimous pass short-circuits past the adjudicator (adjudicated=False)
  - disagreement routes through the adjudicator (adjudicated=True)
  - a failed critic degrades gracefully (verdict still produced, failure recorded)
"""

import src.graph.nodes as nodes
from src.graph.build_graph import run_arbitration
from src.schemas.critique import CritiqueReport, Issue, Severity
from src.schemas.verdict import Verdict


class FakeCritic:
    def __init__(self, dimension, report=None, raise_exc=False):
        self.dimension = dimension
        self._report = report
        self._raise = raise_exc

    def critique(self, llm_output, original_prompt=None):
        if self._raise:
            raise RuntimeError(f"{self.dimension} provider down")
        return self._report


def _report(dim, score, issues=(), conf=0.9):
    return CritiqueReport(
        dimension=dim, score=score, issues=list(issues), confidence=conf, critic_model="fake"
    )


def _patch_critics(monkeypatch, accuracy, logic, completeness):
    monkeypatch.setattr(nodes, "AccuracyCritic", lambda: accuracy)
    monkeypatch.setattr(nodes, "LogicCritic", lambda: logic)
    monkeypatch.setattr(nodes, "CompletenessCritic", lambda: completeness)


def test_unanimous_pass_short_circuits(monkeypatch):
    _patch_critics(
        monkeypatch,
        FakeCritic("accuracy", _report("accuracy", 5)),
        FakeCritic("logic", _report("logic", 5)),
        FakeCritic("completeness", _report("completeness", 4)),
    )
    state = run_arbitration("a clean, correct answer", "a question")
    verdict: Verdict = state["verdict"]
    assert verdict is not None
    assert verdict.adjudicated is False  # short-circuited
    assert verdict.disagreements == []
    assert verdict.confirmed_issues == []


def test_disagreement_routes_to_adjudicator(monkeypatch):
    # accuracy finds a high-severity issue; others score high & clean -> presence_mismatch.
    bad = _report("accuracy", 2, [Issue(quote="Triton orbits Mars", problem="false", severity=Severity.HIGH)])
    _patch_critics(
        monkeypatch,
        FakeCritic("accuracy", bad),
        FakeCritic("logic", _report("logic", 5)),
        FakeCritic("completeness", _report("completeness", 5)),
    )

    sentinel = Verdict(overall_score=4, confidence=0.6, summary="adjudicated", adjudicated=True)
    captured = {}

    def fake_adjudicate(llm_output, original_prompt, reports, disagreements, failed_critics=None):
        captured["disagreements"] = disagreements
        captured["reports"] = reports
        return sentinel

    monkeypatch.setattr(nodes, "adjudicate", fake_adjudicate)

    state = run_arbitration("Triton orbits Mars and other claims", "tell me about Mars")
    assert state["verdict"] is sentinel  # went through the adjudicator
    assert len(captured["disagreements"]) >= 1
    assert any(d.type == "presence_mismatch" for d in state["disagreements"])


def test_failed_critic_degrades_gracefully(monkeypatch):
    _patch_critics(
        monkeypatch,
        FakeCritic("accuracy", _report("accuracy", 5)),
        FakeCritic("logic", None, raise_exc=True),  # this one dies
        FakeCritic("completeness", _report("completeness", 5)),
    )

    def fake_adjudicate(llm_output, original_prompt, reports, disagreements, failed_critics=None):
        # Only two critics should survive.
        assert len(reports) == 2
        assert failed_critics == ["logic"]
        return Verdict(
            overall_score=6, confidence=0.5, summary="degraded", adjudicated=True
        )

    monkeypatch.setattr(nodes, "adjudicate", fake_adjudicate)

    state = run_arbitration("some output", "some question")
    assert state["failed_critics"] == ["logic"]
    assert state["verdict"] is not None
    assert state["logic_report"] is None
