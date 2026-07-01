"""Data contract for an individual critic's report.

Every critic — regardless of provider — must return one of these objects.
`instructor` validates the model's response against this schema, so a malformed
or partial answer fails loudly instead of degrading into unstructured text.
"""

from enum import Enum
from typing import List, Literal

from pydantic import BaseModel, Field, model_validator


def unwrap_envelope(data):
    """Tolerate local models that wrap the object in a single outer key.

    e.g. llama3 in JSON mode sometimes returns {"CritiqueReport": {...real fields...}}
    instead of the flat object. If we see exactly one top-level key whose value is a
    dict, unwrap it so schema validation sees the real fields. No-op for clean input.
    """
    if isinstance(data, dict) and len(data) == 1:
        (only_value,) = data.values()
        if isinstance(only_value, dict):
            return only_value
    return data


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Numeric mapping used by the disagreement detector's `severity_gap` check.
SEVERITY_RANK = {Severity.LOW: 1, Severity.MEDIUM: 3, Severity.HIGH: 5}


class Issue(BaseModel):
    quote: str = Field(
        ..., description="Exact substring copied verbatim from the evaluated output."
    )
    problem: str = Field(..., description="What is wrong with the quoted text.")
    severity: Severity = Field(..., description="How serious the issue is.")


class CritiqueReport(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _unwrap(cls, data):
        return unwrap_envelope(data)

    dimension: Literal["accuracy", "logic", "completeness"] = Field(
        ..., description="Which quality dimension this critic evaluated."
    )
    score: int = Field(
        ..., ge=1, le=5, description="1 (very poor) to 5 (excellent) on this dimension."
    )
    issues: List[Issue] = Field(
        default_factory=list, description="Concrete problems found, each with a verbatim quote."
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="Critic's self-reported confidence in its own judgment."
    )
    critic_model: str = Field(
        ..., description='Model that produced this report, e.g. "gpt-4o", "claude-sonnet-4-6", "llama3".'
    )
