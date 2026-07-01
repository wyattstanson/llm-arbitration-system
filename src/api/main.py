"""FastAPI application entrypoint.

Run with:  uvicorn src.api.main:app --reload
Docs at:   http://localhost:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.api.routes import router
from src.storage.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # ensure the audit-trail table exists before serving
    yield


app = FastAPI(
    title="LLM Output Arbitration System",
    version="0.1.0",
    description=(
        "Three independent critic agents evaluate an LLM output across accuracy, logic, "
        "and completeness; a disagreement detector finds where they conflict; an adjudicator "
        "resolves the conflicts into one confidence-scored, evidence-backed verdict."
    ),
    lifespan=lifespan,
)

# Allow the Vite dev server (and any local origin) to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"], summary="Health check + active provider config")
def health() -> dict:
    return {"status": "ok", "providers": config.provider_summary()}


app.include_router(router)
