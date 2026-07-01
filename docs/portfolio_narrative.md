# Portfolio Narrative

## The one-liner

> *"I built a system where AI models audit each other's work — three specialized critics,
> each on a different model, independently evaluate any LLM output, and an adjudicator
> resolves their disagreements into a single evidence-backed verdict."*

## The problem it solves

Using one model to grade its own (or another model's) output inherits that model's blind
spots. If you ask GPT-4o "is this GPT-4o answer good?", it tends to agree with itself.
The fix isn't a better single judge — it's **disagreement between differently-sourced
judges**, surfaced rather than averaged away.

## How to demo it in 90 seconds

1. **Show the critics disagree.** `python scripts/run_critics.py factually_incorrect`.
   The accuracy critic catches the Triton error; the logic critic catches a non-sequitur
   the accuracy critic framed differently. Different models, different catches.
2. **Show the full verdict.** `python scripts/run_graph.py factually_incorrect`. The
   adjudicator confirms real issues and **dismisses weak flags with reasons** — it's
   resolving, not averaging.
3. **Show the audit trail.** `python scripts/show_arbitration.py <id>` re-fetches the exact
   verdict from SQLite.
4. **Show it at scale.** The Streamlit Batch tab runs a list and produces a sortable table.

## The money slide: a real failure that proves the thesis

On local-Llama-only mode, the adjudicator dismissed a *correct* objection ("humans could
breathe Mars' air unaided") by citing the output's own false claim that the atmosphere is
"oxygen-rich." A single model auditing itself was fooled by the very text it was auditing.

This is the strongest evidence for the architecture: **blind-spot diversity matters.**
With a different, stronger adjudicator model (a real API key), the error vanishes. The
system doesn't hide this — it makes the failure visible and explains why the design
prevents it.

## What a reviewer should take away

- Genuine multi-agent orchestration (LangGraph parallel fan-out/fan-in), not a prompt chain.
- Schema-validated model I/O everywhere (`instructor` + Pydantic) — production-minded.
- The interesting engineering is in **disagreement detection and evidence-based
  adjudication**, both unit-tested.
- Honest engineering: documented tradeoffs (key gap, local-model latency), graceful
  degradation, and a real, reproducible limitation used as a teaching point.
