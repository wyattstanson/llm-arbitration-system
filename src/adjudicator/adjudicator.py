"""Adjudicator agent — resolves critic disagreements into one evidence-backed verdict.

The adjudicator's job is NOT to average three scores. It reasons through each
detected disagreement, decides which critic to side with and why, and produces a
verdict that separates *confirmed* issues from *dismissed* flags (with reasons for
the dismissals). That reasoning is the system's value-add over single-model grading.

Model selection mirrors the critics: prefer a hosted model when a key exists,
otherwise fall back to local Llama so the pipeline always runs.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from src import config
from src.critics.providers import structured_call
from src.schemas.critique import CritiqueReport, unwrap_envelope
from src.schemas.verdict import (
    ConfirmedIssue,
    Disagreement,
    DismissedFlag,
    Verdict,
)


class AdjudicationDecision(BaseModel):
    """What the adjudicator model produces. The graph wraps this into a full Verdict
    by attaching the raw critic reports and the detected disagreements (audit trail)."""

    @model_validator(mode="before")
    @classmethod
    def _unwrap(cls, data):
        return unwrap_envelope(data)

    overall_score: int = Field(..., ge=1, le=10, description="Overall output quality, 1-10.")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in this verdict.")
    confirmed_issues: List[ConfirmedIssue] = Field(default_factory=list)
    dismissed_flags: List[DismissedFlag] = Field(default_factory=list)
    summary: str = Field(..., description="One-paragraph plain-English verdict.")


_SYSTEM = """You are the ADJUDICATOR in a multi-agent output-auditing system.
Three independent critics — accuracy, logic, and completeness — each evaluated the
same LLM output using a DIFFERENT underlying model, so their blind spots differ.
A disagreement detector has flagged where they conflict.

Your job is to RESOLVE conflict with evidence, NOT to average their scores. For each
disagreement you MUST reason it through explicitly:
- Factual disagreement: attempt to verify the claim yourself before ruling.
- Logic disagreement: trace the argument step by step; don't take a critic's word.
- Completeness disagreement: re-read the original question and decide what was
  actually required before deciding whether a gap is real.

Then produce:
- confirmed_issues: problems you judge REAL, each with evidence and which critic(s)
  raised it (use their dimension names: accuracy/logic/completeness).
- dismissed_flags: problems a critic raised that you OVERRULE, each with the critic
  that raised it and your reasoning for dismissing it. If a critic over-flagged or
  mis-scored, this is where you say so — do not rubber-stamp every flag.
- overall_score: 1-10 holistic quality of the output (NOT an average of critic scores).
- confidence: 0-1.
- summary: one paragraph a non-expert can read.

Be willing to side against a critic when the evidence warrants it.

Return ONE flat JSON object whose TOP-LEVEL keys are exactly: overall_score,
confidence, confirmed_issues, dismissed_flags, summary. Do NOT wrap it in an outer
key (e.g. do not nest everything under "AdjudicationDecision"). No prose outside JSON."""


def _format_reports(reports: List[CritiqueReport]) -> str:
    blocks = []
    for r in reports:
        lines = [f"[{r.dimension.upper()} critic — model={r.critic_model}] score={r.score}/5 confidence={r.confidence:.2f}"]
        if not r.issues:
            lines.append("  (no issues found)")
        for iss in r.issues:
            lines.append(f'  - [{iss.severity.value}] {iss.problem} | quote: "{iss.quote}"')
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _format_disagreements(disagreements: List[Disagreement]) -> str:
    if not disagreements:
        return "(none detected)"
    return "\n\n".join(
        f"[{d.type}] {d.description}\n  involved: {', '.join(d.critics_involved)}\n  details: {d.details}"
        for d in disagreements
    )


def adjudicate(
    llm_output: str,
    original_prompt: Optional[str],
    reports: List[CritiqueReport],
    disagreements: List[Disagreement],
    failed_critics: Optional[List[str]] = None,
) -> Verdict:
    failed_critics = failed_critics or []
    provider, model = config.resolve_adjudicator()

    user_prompt = f"""=== ORIGINAL PROMPT / QUESTION ===
{original_prompt or "(none provided)"}

=== OUTPUT BEING EVALUATED ===
{llm_output}

=== CRITIC REPORTS ===
{_format_reports(reports)}

=== DETECTED DISAGREEMENTS ===
{_format_disagreements(disagreements)}

Now adjudicate. Reason through each disagreement, then produce the structured verdict."""

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    decision: AdjudicationDecision = structured_call(
        provider, model, messages, AdjudicationDecision
    )

    confidence = decision.confidence
    summary = decision.summary
    if failed_critics:
        # Graceful degradation: a dimension wasn't assessed -> lower confidence + note it.
        confidence = round(confidence * 0.75, 3)
        summary += (
            f" NOTE: the following critic(s) failed and their dimension was not assessed: "
            f"{', '.join(failed_critics)}. Confidence has been reduced accordingly."
        )

    return Verdict(
        overall_score=decision.overall_score,
        confidence=confidence,
        confirmed_issues=decision.confirmed_issues,
        dismissed_flags=decision.dismissed_flags,
        summary=summary,
        critic_reports=reports,
        disagreements=disagreements,
        adjudicated=True,
    )
