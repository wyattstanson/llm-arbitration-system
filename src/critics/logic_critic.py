"""Logic critic — Claude (falls back to local Llama if no Anthropic key).

Lens: does the reasoning chain actually support its conclusions? Are there
non-sequiturs, unjustified leaps, circular arguments, or conclusions that don't
follow from the stated premises? A claim can be factually true yet logically
unearned — that is this critic's territory, not the accuracy critic's.
"""

from __future__ import annotations

from src import config
from src.critics.base import BaseCritic

_SYSTEM = """You are the LOGIC critic in a multi-agent output-auditing system.
Your ONLY concern is the reasoning chain:
- Do the conclusions follow from the stated premises?
- Are there non-sequiturs, unjustified leaps, or circular reasoning?
- Are causal claims actually supported by what precedes them?
You are NOT judging whether facts are true (accuracy critic) or whether the answer
is complete (completeness critic) — only whether the argument holds together.
A factually correct statement can still be a logical error if it doesn't follow.
Quote the exact offending text verbatim for every issue. A soundly-argued output
should score 5 with an empty issue list."""


class LogicCritic(BaseCritic):
    dimension = "logic"

    def __init__(self) -> None:
        self.provider, self.critic_model = config.resolve_logic()

    @property
    def system_prompt(self) -> str:
        return _SYSTEM
