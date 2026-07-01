"""Accuracy critic — GPT-4o (falls back to local Llama if no OpenAI key).

Lens: are the claims factually correct, verifiable, and internally consistent?
Does the output state things that are false, unsupported, or contradict itself?
"""

from __future__ import annotations

from src import config
from src.critics.base import BaseCritic

_SYSTEM = """You are the ACCURACY critic in a multi-agent output-auditing system.
Your ONLY concern is factual correctness and internal consistency:
- Are factual claims true and verifiable?
- Are there unsupported assertions stated as fact?
- Does the output contradict itself anywhere?
You are NOT judging logical structure or completeness — other critics own those.
Be specific: every issue must quote the exact offending text verbatim. Do not be
lenient to be polite, and do not invent problems that aren't there. A flawless
output should score 5 with an empty issue list."""


class AccuracyCritic(BaseCritic):
    dimension = "accuracy"

    def __init__(self) -> None:
        self.provider, self.critic_model = config.resolve_accuracy()

    @property
    def system_prompt(self) -> str:
        return _SYSTEM
