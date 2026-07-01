"""Request/response models for the API. Rich field descriptions so the
auto-generated OpenAPI docs at /docs are actually readable."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from src.schemas.verdict import Verdict


class ArbitrateRequest(BaseModel):
    llm_output: str = Field(..., description="The LLM-generated text to audit.")
    original_prompt: Optional[str] = Field(
        None, description="The prompt/question the output was responding to, if available."
    )


class ArbitrateResponse(BaseModel):
    id: str = Field(..., description="UUID of the stored arbitration.")
    verdict: Verdict = Field(..., description="The adjudicated verdict.")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp of when it was recorded.")


class BatchRequest(BaseModel):
    items: List[ArbitrateRequest] = Field(..., description="Outputs to arbitrate in one call.")


class BatchItemResult(BaseModel):
    id: str
    verdict: Verdict


class BatchResponse(BaseModel):
    results: List[BatchItemResult]


class ArbitrationDetail(BaseModel):
    id: str
    created_at: str
    original_prompt: Optional[str]
    llm_output: str
    verdict: Verdict


class ArbitrationSummary(BaseModel):
    id: str
    created_at: str
    overall_score: int
    confidence: float
    adjudicated: bool
    output_excerpt: str
    confirmed_issue_count: int
    disagreement_count: int
