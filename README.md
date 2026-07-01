# ⚖️ LLM Output Arbitration System

**Most AI projects generate answers. This one catches bad answers.**

It takes any LLM-generated output, sends it to **three specialized critic agents** — each running a *different* model so they don't share blind spots — detects where those critics **disagree**, and routes the disagreements to an **adjudicator agent** that resolves them into a single, evidence-backed verdict.

> The whole value of the system is the *disagreement between differently-sourced critics*. That disagreement is the signal, not noise to be averaged away.

---

## The architecture (parallel fan-out / fan-in)

```
                         ┌────────────────────┐
                         │     llm_output     │
                         │  (+ original prompt)│
                         └─────────┬──────────┘
                                   │  parse_input
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼          ← run in PARALLEL
   ┌──────────────────┐ ┌──────────────────┐ ┌────────────────────┐
   │ ACCURACY  critic │ │  LOGIC   critic  │ │ COMPLETENESS critic│
   │   GPT-4o         │ │  Claude          │ │  local Llama       │
   │ (facts)          │ │ (reasoning)      │ │ (coverage)         │
   └────────┬─────────┘ └────────┬─────────┘ └─────────┬──────────┘
            └────────────────────┼─────────────────────┘
                                 ▼  collect_critiques (fan-in)
                       ┌───────────────────────┐
                       │ detect_disagreements  │  presence_mismatch
                       │  (3 rules)            │  severity_gap
                       └───────────┬───────────┘  unique_find
                                   │
                    unanimous pass │ disagreement / failure
                   ┌───────────────┴───────────────┐
                   ▼                               ▼
        ┌────────────────────┐          ┌────────────────────┐
        │  short-circuit     │          │   ADJUDICATOR      │
        │  (adjudicated=     │          │  resolves each     │
        │   False)           │          │  conflict w/ evidence│
        └─────────┬──────────┘          └─────────┬──────────┘
                  └───────────────┬───────────────┘
                                  ▼
                          ┌───────────────┐
                          │    Verdict    │ → SQLite audit trail
                          └───────────────┘
```

**Why different models per critic?** If all three critics ran on the same model, they'd
share the same failure modes and would never genuinely disagree. Diversity of *source*
is what makes the disagreement signal meaningful.

---

## What makes this more than a wrapper

1. **Different model per critic** — accuracy→GPT-4o, logic→Claude, completeness→local Llama. (Auto-falls back to local Llama for any provider whose key is absent, so it runs key-free.)
2. **Critics run in parallel** — no critic sees another's judgment first (avoids anchoring bias). Real LangGraph fan-out, not a sequential await chain.
3. **Every model call is schema-validated** via `instructor` + Pydantic — a malformed response fails loudly instead of silently degrading into text you have to regex-parse.
4. **Disagreement detection is explicit** — three rules (`presence_mismatch`, `severity_gap`, `unique_find`), each unit-tested, never averaged away.
5. **The adjudicator resolves with evidence, not arithmetic** — it reasons through each disagreement and separates *confirmed* issues from *dismissed* flags (with reasons for the dismissals).
6. **Durable audit trail** — every arbitration (inputs, all critic reports, disagreements, verdict) is persisted to SQLite and replayable by ID.
7. **Graceful degradation** — kill a critic mid-run and you still get a verdict, with the missing dimension recorded and confidence lowered.

---

## A real finding from a live run (this is the pitch)

Run the planted-error Mars fixture through the system on **local Llama only** (no keys),
and the adjudicator does this:

- ✅ Correctly confirms *"Mars is larger than Earth"* and *"Triton is a moon of Mars"* as false.
- ❌ **Dismisses the logic critic's correct objection** to *"humans could breathe unaided"*,
  reasoning that *"the output provides context about Mars' atmosphere being oxygen-rich,
  which could be sufficient for human respiration."*

The adjudicator got **fooled by the output's own false premise** (Mars' atmosphere is 95% CO₂).
A *single* model auditing itself inherits its own gullibility — which is exactly why the
architecture mandates a different, stronger model for adjudication. Drop in a real
`OPENAI_API_KEY` and that bad dismissal disappears and the `6/10` becomes a `2/10`.

**The system honestly exposes its own limitation** — and demonstrates, on real data, why
multi-model critique beats single-model self-evaluation.

---

## Quickstart

### Option A — local, no Docker (what this repo was built/tested on)
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows;  source .venv/bin/activate on *nix
pip install -e ".[dev]"
cp .env.example .env              # optional: add OPENAI/ANTHROPIC keys for real diversity

# 1) Run the three critics on a fixture and watch them disagree
python scripts/run_critics.py logically_flawed

# 2) Run the full pipeline → verdict, persisted to SQLite
python scripts/run_graph.py factually_incorrect
python scripts/show_arbitration.py        # list stored arbitrations

# 3) The API
uvicorn src.api.main:app --reload         # http://localhost:8000/docs

# 4) The UI
streamlit run ui/app.py                   # http://localhost:8501
```

### Option B — Docker (authored; **untested on the build machine**, which has no Docker)
```bash
cp .env.example .env
docker compose up        # API :8000/docs, UI :8501, Ollama auto-pulls llama3
```

> **Key gap, stated plainly:** running Ollama removes the key requirement only for the
> *completeness* critic. The accuracy and logic critics still need real OpenAI/Anthropic
> keys — without them they fall back to local Llama. For a fully key-free demo set
> `ARBITRATION_MODE=local_only` (all three critics use Ollama; disagreement quality is
> lower because the blind-spot-diversity argument weakens when one model grades itself
> three times).

---

## API

| Endpoint | Purpose |
|---|---|
| `POST /v1/arbitrate` | Arbitrate one output → `{id, verdict, created_at}` |
| `POST /v1/arbitrate/batch` | Arbitrate many → `{results: [...]}` |
| `GET /v1/arbitrations/{id}` | Fetch a stored arbitration (or 404) |
| `GET /v1/analytics` | Live aggregate stats over all arbitrations |
| `GET /health` | Status + active provider config |

Full interactive docs auto-generated at `/docs`.

---

## Tech stack

Python 3.11+ · **LangGraph** (state graph, parallel fan-out/fan-in) · **instructor + Pydantic**
(schema-validated model calls) · OpenAI / Anthropic / Ollama · **tenacity** (retry/backoff) ·
**SQLite** (audit trail) · **FastAPI** (auto OpenAPI) · **Streamlit** (verdict explorer) ·
Docker Compose.

---

## Testing

```bash
pytest -q          # 35 tests, no API keys required
```

The suite covers schema validation, all three disagreement rules, graph orchestration
(short-circuit, adjudication routing, graceful degradation), the SQLite round-trip, the
API endpoints, and the UI's quote-highlighting. Live model calls are reserved for the
runnable scripts, not the unit tests.

See [docs/architecture.md](docs/architecture.md) and
[docs/portfolio_narrative.md](docs/portfolio_narrative.md) for more.
