"""Shared critic interface.

Every critic — accuracy (GPT-4o), logic (Claude), completeness (Llama) — subclasses
`BaseCritic`. They differ only in: which dimension they own, which provider/model
they call, and their system prompt. Everything else (instructor wiring, the retry
loop, schema enforcement) lives here so the three critics stay interchangeable.

The contract: `critique(llm_output, original_prompt) -> CritiqueReport`, always
schema-valid, regardless of provider.
"""

from __future__ import annotations

import abc

from tenacity import retry, stop_after_attempt, wait_exponential

from src.critics.providers import structured_call
from src.schemas.critique import CritiqueReport

# How the user-facing critique request is framed for every provider.
_USER_TEMPLATE = """You are evaluating the following LLM-generated OUTPUT.

{prompt_block}=== OUTPUT TO EVALUATE ===
{llm_output}
=== END OUTPUT ===

Evaluate ONLY the "{dimension}" dimension. Return a structured report:
- score: integer 1-5 for this dimension (1 = very poor, 5 = excellent).
- issues: a list of concrete problems. For EACH issue include:
    - quote: an EXACT substring copied verbatim from the output above.
    - problem: what is wrong with it.
    - severity: one of "low", "medium", "high".
  If you find no issues, return an empty list.
- confidence: float 0-1, how sure you are of your own judgment.
- critic_model: set this to "{critic_model}".
- dimension: set this to "{dimension}".
Do not evaluate dimensions other than {dimension}."""


class BaseCritic(abc.ABC):
    #: "accuracy" | "logic" | "completeness"
    dimension: str
    #: identifier stored in the report AND used as the API model id, e.g. "gpt-4o"
    critic_model: str
    #: "openai" | "anthropic" | "groq" | "ollama" — resolved per critic in __init__
    provider: str

    @property
    @abc.abstractmethod
    def system_prompt(self) -> str:
        """Dimension-specific instructions that define this critic's lens."""

    def _create(self, system_prompt: str, user_prompt: str) -> CritiqueReport:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return structured_call(self.provider, self.critic_model, messages, CritiqueReport)

    def _build_user_prompt(self, llm_output: str, original_prompt: str | None) -> str:
        prompt_block = (
            f"=== ORIGINAL PROMPT / QUESTION ===\n{original_prompt}\n=== END PROMPT ===\n\n"
            if original_prompt
            else "(No original prompt was provided — evaluate the output on its own terms.)\n\n"
        )
        return _USER_TEMPLATE.format(
            prompt_block=prompt_block,
            llm_output=llm_output,
            dimension=self.dimension,
            critic_model=self.critic_model,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def critique(self, llm_output: str, original_prompt: str | None = None) -> CritiqueReport:
        user_prompt = self._build_user_prompt(llm_output, original_prompt)
        report = self._create(self.system_prompt, user_prompt)
        # Defensive: ensure the model didn't mislabel the dimension/model.
        report.dimension = self.dimension  # type: ignore[assignment]
        report.critic_model = self.critic_model
        return report
