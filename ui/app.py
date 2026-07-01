"""Streamlit verdict explorer.

A reviewer with zero context should be able to open this, paste an LLM output, and
understand the verdict without reading any code. Four tabs:
  - Arbitrate    : run a new arbitration (or load a fixture) and explore the verdict
  - Stored       : browse past arbitrations from the SQLite audit trail (instant)
  - Batch        : submit many outputs at once, view a sortable results table
  - Analytics    : live dashboard over all stored arbitrations

Note: running a NEW arbitration calls the live pipeline. On CPU-only local Llama
that takes minutes; with hosted keys it's seconds. Browsing stored verdicts is instant.
"""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.analytics.metrics import compute_analytics  # noqa: E402
from src.service import arbitrate_and_store  # noqa: E402
from src.storage.db import get_arbitration, list_arbitrations  # noqa: E402
from ui.render import SEV_COLOR, highlight_output  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"

DIM_COLOR = {"accuracy": "#4dabf7", "logic": "#9775fa", "completeness": "#69db7c"}

st.set_page_config(page_title="LLM Arbitration", layout="wide", page_icon="⚖️")


# ----------------------------------------------------------------------------- helpers
def render_verdict(rec):
    v = rec.verdict
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall score", f"{v.overall_score}/10")
    c2.metric("Confidence", f"{v.confidence:.0%}")
    c3.metric("Adjudicated", "Yes" if v.adjudicated else "No (short-circuit)")
    c4.metric("Disagreements", len(v.disagreements))
    st.info(v.summary)

    st.markdown("#### Output with inline issue markers")
    st.caption("Hover a highlight to see which critic flagged it and why. "
               "Red = high severity · orange = medium · yellow = low.")
    st.markdown(
        f'<div style="line-height:1.7;font-size:0.95rem;padding:0.5rem;border:1px solid #444;'
        f'border-radius:6px;">{highlight_output(rec.llm_output, v.critic_reports)}</div>',
        unsafe_allow_html=True,
    )

    col_conf, col_dis = st.columns(2)
    with col_conf:
        st.markdown(f"#### ✅ Confirmed issues ({len(v.confirmed_issues)})")
        for ci in v.confirmed_issues:
            with st.expander(f"[{ci.severity.value.upper()}] {ci.description[:70]}"):
                st.write(f"**Evidence:** {ci.evidence}")
                st.write(f"**Raised by:** {', '.join(ci.source_critics)}")
        if not v.confirmed_issues:
            st.caption("None.")
    with col_dis:
        st.markdown(f"#### ⚠️ Dismissed flags ({len(v.dismissed_flags)})")
        for df in v.dismissed_flags:
            with st.expander(f"[dismissed] {df.description[:70]}"):
                st.write(f"**Raised by:** {df.raised_by}")
                st.write(f"**Adjudicator's reasoning for overruling:** {df.reasoning}")
        if not v.dismissed_flags:
            st.caption("None.")

    render_critic_panel(v)

    if v.disagreements:
        st.markdown("#### 🔀 Detected disagreements")
        for d in v.disagreements:
            st.markdown(f"- `{d.type}` — {d.description}")
            st.caption(d.details)


def render_critic_panel(v):
    st.markdown("#### Critic comparison panel")
    st.caption("The multi-model architecture, side by side. Each column is a different model.")
    cols = st.columns(3)
    reports = {r.dimension: r for r in v.critic_reports}
    for col, dim in zip(cols, ("accuracy", "logic", "completeness")):
        with col:
            r = reports.get(dim)
            color = DIM_COLOR[dim]
            st.markdown(
                f'<div style="border-top:4px solid {color};padding-top:4px;">'
                f'<b>{dim.upper()}</b></div>', unsafe_allow_html=True,
            )
            if r is None:
                st.error("Critic failed — dimension not assessed.")
                continue
            st.write(f"Model: `{r.critic_model}`")
            st.write(f"Score: **{r.score}/5** · Confidence: {r.confidence:.0%}")
            if not r.issues:
                st.success("No issues found.")
            for iss in r.issues:
                st.markdown(
                    f'<span style="color:{SEV_COLOR.get(iss.severity.value)};">●</span> '
                    f'**{iss.severity.value}** — {iss.problem}', unsafe_allow_html=True,
                )


# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("⚖️ LLM Arbitration")
    st.caption("Three critics audit an LLM output; an adjudicator resolves their conflicts.")
    ps = config.provider_summary()
    st.markdown("**Active providers**")
    for k in ("accuracy", "logic", "completeness"):
        st.markdown(f"- {k}: `{ps[k]}`")
    st.markdown(f"**Mode:** `{ps['mode']}`")
    if "local" in ps["accuracy"]:
        st.warning("Running on local Llama — new arbitrations take minutes. "
                   "Add API keys to .env for fast, diverse critics.")

tab_run, tab_stored, tab_batch, tab_analytics = st.tabs(
    ["Arbitrate", "Stored", "Batch", "Analytics"]
)

# ----------------------------------------------------------------------------- Arbitrate
with tab_run:
    st.subheader("Arbitrate an output")
    fixtures = sorted(p.stem for p in FIXTURES.glob("*.json"))
    pick = st.selectbox("Load a fixture (optional)", ["— none —"] + fixtures)
    default_out, default_prompt = "", ""
    if pick != "— none —":
        data = json.loads((FIXTURES / f"{pick}.json").read_text(encoding="utf-8"))
        default_out, default_prompt = data["llm_output"], data.get("original_prompt", "")

    prompt = st.text_area("Original prompt (optional)", value=default_prompt, height=80)
    output = st.text_area("LLM output to audit", value=default_out, height=180)

    if st.button("Run arbitration", type="primary", disabled=not output.strip()):
        with st.spinner("Running three critics + adjudicator…"):
            rec = arbitrate_and_store(output, prompt or None)
        st.success(f"Done. Stored as id `{rec.id}`")
        render_verdict(rec)

# ----------------------------------------------------------------------------- Stored
with tab_stored:
    st.subheader("Stored arbitrations")
    records = list_arbitrations()
    if not records:
        st.caption("Nothing stored yet. Run an arbitration first.")
    else:
        labels = {f"{r.created_at[:19]} · {r.verdict.overall_score}/10 · {r.llm_output[:40]}…": r.id
                  for r in records}
        choice = st.selectbox("Pick one", list(labels))
        if choice:
            rec = get_arbitration(labels[choice])
            if rec:
                render_verdict(rec)

# ----------------------------------------------------------------------------- Batch
with tab_batch:
    st.subheader("Batch mode")
    st.caption('Paste a JSON list: [{"llm_output": "...", "original_prompt": "..."}, ...] '
               "or upload a .json file.")
    uploaded = st.file_uploader("Upload JSON", type="json")
    raw = st.text_area("…or paste JSON here", height=140)
    if st.button("Run batch", type="primary"):
        try:
            payload = json.load(uploaded) if uploaded else json.loads(raw)
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't parse JSON: {e}")
            payload = None
        if payload:
            rows = []
            prog = st.progress(0.0)
            for i, item in enumerate(payload):
                rec = arbitrate_and_store(item["llm_output"], item.get("original_prompt"))
                v = rec.verdict
                rows.append({
                    "id": rec.id[:8],
                    "output excerpt": item["llm_output"][:60],
                    "score": v.overall_score,
                    "issues": len(v.confirmed_issues),
                    "confidence": round(v.confidence, 2),
                    "disagreements": len(v.disagreements),
                })
                prog.progress((i + 1) / len(payload))
            st.dataframe(rows, use_container_width=True)
            st.caption("Click a column header to sort.")

# ----------------------------------------------------------------------------- Analytics
with tab_analytics:
    st.subheader("Analytics (live over all stored arbitrations)")
    stats = compute_analytics()
    if stats.get("total_arbitrations", 0) == 0:
        st.caption("No data yet — run some arbitrations.")
    else:
        a, b, c, d = st.columns(4)
        a.metric("Total", stats["total_arbitrations"])
        b.metric("Avg score", stats["avg_overall_score"])
        c.metric("Disagreement rate", f"{stats['disagreement_rate']:.0%}")
        d.metric("Short-circuit rate", f"{stats['short_circuit_rate']:.0%}")
        st.markdown("**Avg issues per run, by critic**")
        st.bar_chart(stats["avg_issues_per_run_by_critic"])
        cc1, cc2 = st.columns(2)
        cc1.markdown("**Most overruled critic**")
        cc1.write(stats.get("most_overruled_critic") or "—")
        cc1.json(stats.get("overruled_flags_by_critic", {}))
        cc2.markdown("**Disagreement types**")
        cc2.json(stats.get("disagreement_type_counts", {}))
