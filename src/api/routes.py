"""API routes for the arbitration service.

Note on latency: POST /v1/arbitrate runs the full critic+adjudicator pipeline
synchronously. With hosted models that's a few seconds; with local CPU-only Llama
it can be minutes. For production you'd push this onto a task queue — called out
in the README as a known tradeoff rather than hidden.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.analytics.metrics import compute_analytics
from src.api.schemas import (
    ArbitrateRequest,
    ArbitrateResponse,
    ArbitrationDetail,
    ArbitrationSummary,
    BatchItemResult,
    BatchRequest,
    BatchResponse,
)
from src.service import arbitrate_and_store
from src.storage.db import get_arbitration, list_arbitrations

router = APIRouter(prefix="/v1", tags=["arbitration"])


@router.post("/arbitrate", response_model=ArbitrateResponse, summary="Arbitrate one output")
def arbitrate(req: ArbitrateRequest) -> ArbitrateResponse:
    """Run the three critics + adjudicator on one LLM output and persist the verdict."""
    rec = arbitrate_and_store(req.llm_output, req.original_prompt)
    return ArbitrateResponse(id=rec.id, verdict=rec.verdict, created_at=rec.created_at)


@router.post("/arbitrate/batch", response_model=BatchResponse, summary="Arbitrate many outputs")
def arbitrate_batch(req: BatchRequest) -> BatchResponse:
    """Arbitrate a list of outputs; each is stored independently."""
    results = []
    for item in req.items:
        rec = arbitrate_and_store(item.llm_output, item.original_prompt)
        results.append(BatchItemResult(id=rec.id, verdict=rec.verdict))
    return BatchResponse(results=results)


@router.get(
    "/arbitrations",
    response_model=list[ArbitrationSummary],
    summary="List stored arbitrations (newest first)",
)
def list_all(limit: int = 100) -> list[ArbitrationSummary]:
    """Lightweight summaries for the history/list view — newest first."""
    out = []
    for rec in list_arbitrations(limit=limit):
        v = rec.verdict
        out.append(
            ArbitrationSummary(
                id=rec.id,
                created_at=rec.created_at,
                overall_score=v.overall_score,
                confidence=v.confidence,
                adjudicated=v.adjudicated,
                output_excerpt=rec.llm_output[:160],
                confirmed_issue_count=len(v.confirmed_issues),
                disagreement_count=len(v.disagreements),
            )
        )
    return out


@router.get(
    "/arbitrations/{arbitration_id}",
    response_model=ArbitrationDetail,
    summary="Fetch a stored arbitration",
)
def get_one(arbitration_id: str) -> ArbitrationDetail:
    """Return a previously stored arbitration (inputs + verdict + critic reports), or 404."""
    rec = get_arbitration(arbitration_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"No arbitration with id {arbitration_id}")
    return ArbitrationDetail(**rec.model_dump())


@router.get("/analytics", summary="Aggregate analytics over all arbitrations")
def analytics() -> dict:
    """Live stats computed over the full audit trail (issue counts per critic,
    most-overruled critic, disagreement rate, etc.). Recomputed on every call."""
    return compute_analytics()
