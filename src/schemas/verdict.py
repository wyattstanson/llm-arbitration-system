"""Data contract for the adjudicator's final verdict.

The verdict is the system's single output: it carries the resolved issues,
the flags the adjudicator overruled, and — crucially for the audit trail — the
raw critic reports and the disagreements that were detected between them.
"""

from typing import List, Literal

from pydantic import BaseModel, Field

from .critique import CritiqueReport, Severity


class Disagreement(BaseModel):
    type: Literal["presence_mismatch", "severity_gap", "unique_find"] = Field(
        ..., description="Which of the three disagreement rules fired."
    )
    description: str = Field(..., description="Human-readable summary of the disagreement.")
    critics_involved: List[str] = Field(
        ..., description="Critic models / dimensions implicated in this disagreement."
    )
    details: str = Field(..., description="Specific evidence: the quotes and severities in conflict.")


class ConfirmedIssue(BaseModel):
    description: str = Field(..., description="The issue the adjudicator upheld as real.")
    severity: Severity = Field(..., description="Adjudicator's final severity rating.")
    evidence: str = Field(..., description="Why this is a genuine problem.")
    source_critics: List[str] = Field(
        ..., description="Which critic(s) originally raised this issue."
    )


class DismissedFlag(BaseModel):
    description: str = Field(..., description="The flag a critic raised.")
    raised_by: str = Field(..., description="The critic that raised it.")
    reasoning: str = Field(
        ..., description="Why the adjudicator overruled it rather than confirming it."
    )


class Verdict(BaseModel):
    overall_score: int = Field(
        ..., ge=1, le=10, description="Overall quality of the evaluated output, 1 (worst) to 10 (best)."
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="Adjudicator's confidence in this verdict."
    )
    confirmed_issues: List[ConfirmedIssue] = Field(
        default_factory=list, description="Issues upheld with evidence."
    )
    dismissed_flags: List[DismissedFlag] = Field(
        default_factory=list, description="Critic flags the adjudicator overruled, with reasons."
    )
    summary: str = Field(..., description="One-paragraph plain-English verdict.")
    critic_reports: List[CritiqueReport] = Field(
        default_factory=list, description="The raw reports from every critic (audit trail)."
    )
    disagreements: List[Disagreement] = Field(
        default_factory=list, description="Disagreements detected between critics."
    )
    adjudicated: bool = Field(
        ..., description="False if the run short-circuited on a unanimous high-confidence pass."
    )
