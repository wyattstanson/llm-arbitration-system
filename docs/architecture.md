# Architecture

## Pipeline

The system is a LangGraph `StateGraph` over a single `ArbitrationState`:

```
parse_input
  ├─▶ accuracy_critic      ┐
  ├─▶ logic_critic         │  parallel super-step (fan-out)
  └─▶ completeness_critic  ┘
        └─▶ collect_critiques        (fan-in: waits for all three)
              └─▶ detect_disagreements
                    ├─(unanimous high-confidence pass)─▶ short_circuit ─▶ END
                    └─(disagreement or critic failure)─▶ adjudicate    ─▶ END
```

### Why parallel
The three critics are dispatched in the same LangGraph super-step (three edges out of
`parse_input`). No critic sees another's output before forming its own judgment —
sequential critique would introduce anchoring bias, and parallelism also cuts latency.

`failed_critics` carries an additive reducer (`Annotated[List[str], operator.add]`) so the
parallel branches can each append a failure without clobbering one another.

## Data contracts (`src/schemas/`)

- **`CritiqueReport`** — one critic's output: `dimension`, `score` (1–5), `issues`
  (each a verbatim `quote` + `problem` + `severity`), `confidence`, `critic_model`.
- **`Verdict`** — the adjudicator's output: `overall_score` (1–10), `confidence`,
  `confirmed_issues`, `dismissed_flags`, `summary`, plus the raw `critic_reports` and
  detected `disagreements` for the audit trail, and an `adjudicated` flag.

Every model call returns one of these via `instructor`, so malformed responses raise
instead of silently degrading. A tolerant `unwrap_envelope` validator handles a known
local-Llama quirk where the model wraps its JSON in a single outer key.

## Disagreement detection (`src/disagreement/detector.py`)

Two issues are the "same region" when their quotes overlap (substring containment or
token-Jaccard ≥ 0.5). Given that:

| Rule | Fires when |
|---|---|
| `severity_gap` | Two critics flag the same region but rate severity >2 levels apart (low=1, medium=3, high=5 — only low-vs-high, a gap of 4, qualifies). |
| `presence_mismatch` | One critic flags a region **no other critic mentions**, *and* those others scored their own dimension ≥4 (the "confident-clean contradiction"). |
| `unique_find` | One critic flags a region no other mentions, but the others were **not** confident-clean — a category simply nobody else caught. |

This disambiguation keeps every detected conflict mapped to exactly one type. It is an
explicit interpretation of the spec (whose `presence_mismatch` and `unique_find`
descriptions overlap); the distinguishing condition is the other critics' confidence.

## Short-circuit

If there are zero disagreements, no failed critics, and all three critics score ≥4 with
confidence ≥0.8, the graph skips the adjudicator entirely and emits a verdict with
`adjudicated=False`. Saves a model call and is itself a demo-able feature.

## Graceful degradation

Each critic call is wrapped in `tenacity` retry (3 attempts, exponential backoff). If a
critic still fails, its node records the failure in `failed_critics` and returns a `None`
report instead of crashing. The run continues with the surviving critics, the adjudicator
notes the unassessed dimension, and final confidence is reduced.

## Storage (`src/storage/db.py`)

One SQLite row per arbitration; the `Verdict` is serialized as JSON via Pydantic, so a
round-trip reproduces the object exactly. Re-fetchable by UUID for replay/audit.
