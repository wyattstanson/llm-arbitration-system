"""LangGraph node functions for the arbitration pipeline.

Flow:
    parse_input
        -> accuracy_critic  \
        -> logic_critic       >  (run in PARALLEL)
        -> completeness_critic/
        -> collect_critiques  (fan-in: waits for all three)
        -> detect_disagreements
        -> [conditional] short-circuit on unanimous pass, else adjudicate
        -> END

Each critic node is wrapped so a provider failure degrades gracefully: the report
becomes None and the critic's name is recorded in `failed_critics` instead of
crashing the run.
"""

from __future__ import annotations

from src.adjudicator.adjudicator import adjudicate
from src.critics import AccuracyCritic, CompletenessCritic, LogicCritic
from src.disagreement.detector import detect_disagreements
from src.graph.state import ArbitrationState
from src.schemas.verdict import Verdict

# Short-circuit thresholds (documented assumptions).
PASS_SCORE = 4
PASS_CONFIDENCE = 0.8


def parse_input(state: ArbitrationState) -> dict:
    if not state.get("llm_output", "").strip():
        raise ValueError("llm_output is empty — nothing to arbitrate.")
    return {"llm_output": state["llm_output"], "original_prompt": state.get("original_prompt")}


def _run_critic(critic, state: ArbitrationState, report_key: str) -> dict:
    try:
        report = critic.critique(state["llm_output"], state.get("original_prompt"))
        return {report_key: report}
    except Exception:  # noqa: BLE001 — degrade, don't crash the whole run
        return {report_key: None, "failed_critics": [critic.dimension]}


def accuracy_node(state: ArbitrationState) -> dict:
    return _run_critic(AccuracyCritic(), state, "accuracy_report")


def logic_node(state: ArbitrationState) -> dict:
    return _run_critic(LogicCritic(), state, "logic_report")


def completeness_node(state: ArbitrationState) -> dict:
    return _run_critic(CompletenessCritic(), state, "completeness_report")


def collect_critiques(state: ArbitrationState) -> dict:
    """Fan-in join. Nothing to compute — its purpose is to wait for all three critics."""
    return {}


def detect_disagreements_node(state: ArbitrationState) -> dict:
    reports = [
        state.get("accuracy_report"),
        state.get("logic_report"),
        state.get("completeness_report"),
    ]
    return {"disagreements": detect_disagreements(reports)}


def _present_reports(state: ArbitrationState):
    return [
        r
        for r in (
            state.get("accuracy_report"),
            state.get("logic_report"),
            state.get("completeness_report"),
        )
        if r is not None
    ]


def should_adjudicate(state: ArbitrationState) -> str:
    """Conditional edge: skip the adjudicator on a unanimous high-confidence pass."""
    if state.get("failed_critics"):
        return "adjudicate"  # a missing dimension always needs adjudication
    if state.get("disagreements"):
        return "adjudicate"
    reports = _present_reports(state)
    if len(reports) < 3:
        return "adjudicate"
    if all(r.score >= PASS_SCORE and r.confidence >= PASS_CONFIDENCE for r in reports):
        return "short_circuit"
    return "adjudicate"


def short_circuit_node(state: ArbitrationState) -> dict:
    """Unanimous pass: build a high-confidence verdict WITHOUT calling the adjudicator."""
    reports = _present_reports(state)
    mean_score = sum(r.score for r in reports) / len(reports)
    overall = max(1, min(10, round(mean_score / 5 * 10)))
    confidence = min(r.confidence for r in reports)
    verdict = Verdict(
        overall_score=overall,
        confidence=confidence,
        confirmed_issues=[],
        dismissed_flags=[],
        summary=(
            "Unanimous high-confidence pass: all three critics scored the output highly "
            "with no disagreements, so adjudication was skipped (short-circuit path)."
        ),
        critic_reports=reports,
        disagreements=[],
        adjudicated=False,
    )
    return {"verdict": verdict}


def adjudicate_node(state: ArbitrationState) -> dict:
    verdict = adjudicate(
        llm_output=state["llm_output"],
        original_prompt=state.get("original_prompt"),
        reports=_present_reports(state),
        disagreements=state.get("disagreements", []),
        failed_critics=state.get("failed_critics", []),
    )
    return {"verdict": verdict}
