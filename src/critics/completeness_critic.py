"""Completeness critic — local Llama via Ollama (always local by design).

Lens: does the response actually address every part of the original question?
Multi-part questions, implicit sub-requirements, and the asker's real intent are
what this critic guards. An answer can be accurate and logically sound yet still
ignore half of what was asked — that gap is this critic's job to surface.

Uses Ollama JSON mode because local models don't do native tool-calling reliably.
"""

from __future__ import annotations

from src import config
from src.critics.base import BaseCritic

_SYSTEM = """You are the COMPLETENESS critic in a multi-agent output-auditing system.
Your ONLY concern is whether the output fully addresses what was actually asked:
- Does it answer every part of a multi-part question?
- Does it satisfy the real intent, not just the literal words?
- Are there obvious gaps, skipped sub-questions, or unaddressed requirements?
You are NOT judging factual correctness (accuracy critic) or reasoning validity
(logic critic) — only coverage of the request.
If no original prompt was provided, judge whether the output is self-contained and
leaves no obvious dangling gaps. Quote the exact relevant text verbatim for every
issue. A fully-complete answer should score 5 with an empty issue list.

Respond ONLY with a JSON object matching the required schema. No prose outside JSON."""


class CompletenessCritic(BaseCritic):
    dimension = "completeness"

    def __init__(self) -> None:
        # Always local by design — this is the deliberate diversity anchor.
        self.provider, self.critic_model = "ollama", config.OLLAMA_MODEL

    @property
    def system_prompt(self) -> str:
        return _SYSTEM
