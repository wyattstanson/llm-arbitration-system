"""Application service layer: run an arbitration and persist it.

Keeps the graph pure (no storage side-effects, so it stays trivially testable) while
giving the API and scripts a single call that both arbitrates and records the result.
"""

from __future__ import annotations

from typing import Optional

from src.graph.build_graph import run_arbitration
from src.storage.db import ArbitrationRecord, save_arbitration


def arbitrate_and_store(
    llm_output: str, original_prompt: Optional[str] = None
) -> ArbitrationRecord:
    state = run_arbitration(llm_output, original_prompt)
    verdict = state["verdict"]
    return save_arbitration(llm_output, original_prompt, verdict)
