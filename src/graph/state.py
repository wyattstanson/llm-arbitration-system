"""Shared state object that flows through the LangGraph arbitration pipeline.

`failed_critics` uses an additive reducer because the three critic nodes run in
PARALLEL — each may append the name of a critic that failed, and LangGraph must
merge those concurrent writes instead of letting one branch overwrite another.
"""

import operator
from typing import Annotated, List, Optional, TypedDict

from src.schemas.critique import CritiqueReport
from src.schemas.verdict import Disagreement, Verdict


class ArbitrationState(TypedDict):
    original_prompt: Optional[str]
    llm_output: str
    accuracy_report: Optional[CritiqueReport]
    logic_report: Optional[CritiqueReport]
    completeness_report: Optional[CritiqueReport]
    failed_critics: Annotated[List[str], operator.add]  # merged across parallel branches
    disagreements: List[Disagreement]
    verdict: Optional[Verdict]
