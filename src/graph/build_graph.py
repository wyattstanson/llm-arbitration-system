"""Assemble the arbitration pipeline as a LangGraph StateGraph.

The fan-out is real parallelism: parse_input has three outgoing edges (one per
critic), so LangGraph dispatches all three critics in the same super-step. They
reconverge at collect_critiques, which only runs once all three have returned.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.graph.nodes import (
    accuracy_node,
    adjudicate_node,
    collect_critiques,
    completeness_node,
    detect_disagreements_node,
    logic_node,
    parse_input,
    short_circuit_node,
    should_adjudicate,
)
from src.graph.state import ArbitrationState


def build_graph():
    g = StateGraph(ArbitrationState)

    g.add_node("parse_input", parse_input)
    g.add_node("accuracy_critic", accuracy_node)
    g.add_node("logic_critic", logic_node)
    g.add_node("completeness_critic", completeness_node)
    g.add_node("collect_critiques", collect_critiques)
    g.add_node("detect_disagreements", detect_disagreements_node)
    g.add_node("adjudicate", adjudicate_node)
    g.add_node("short_circuit", short_circuit_node)

    g.add_edge(START, "parse_input")

    # Fan-out: all three critics dispatched in parallel from parse_input.
    g.add_edge("parse_input", "accuracy_critic")
    g.add_edge("parse_input", "logic_critic")
    g.add_edge("parse_input", "completeness_critic")

    # Fan-in: collect_critiques runs only after all three critics complete.
    g.add_edge("accuracy_critic", "collect_critiques")
    g.add_edge("logic_critic", "collect_critiques")
    g.add_edge("completeness_critic", "collect_critiques")

    g.add_edge("collect_critiques", "detect_disagreements")

    # Conditional: unanimous pass short-circuits past the adjudicator.
    g.add_conditional_edges(
        "detect_disagreements",
        should_adjudicate,
        {"adjudicate": "adjudicate", "short_circuit": "short_circuit"},
    )

    g.add_edge("adjudicate", END)
    g.add_edge("short_circuit", END)

    return g.compile()


def run_arbitration(llm_output: str, original_prompt: str | None = None) -> ArbitrationState:
    """Convenience entrypoint: run the full pipeline and return the final state."""
    graph = build_graph()
    initial: ArbitrationState = {
        "original_prompt": original_prompt,
        "llm_output": llm_output,
        "accuracy_report": None,
        "logic_report": None,
        "completeness_report": None,
        "failed_critics": [],
        "disagreements": [],
        "verdict": None,
    }
    return graph.invoke(initial)
