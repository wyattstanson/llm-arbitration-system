"""Pure rendering helpers for the Streamlit UI — no Streamlit imports, so they're
unit-testable without a browser. The interesting one is highlight_output, which
maps each critic's verbatim quote back onto the original text as a colored span."""

from __future__ import annotations

SEV_COLOR = {"high": "#ff6b6b", "medium": "#ffa94d", "low": "#ffd43b"}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def highlight_output(text: str, reports) -> str:
    """Wrap every critic-flagged quote found in `text` with a severity-colored span.

    Overlapping flags are resolved by keeping the earliest-starting, then longest,
    span — so the same character is never wrapped twice (which would break the HTML).
    Quotes that don't appear verbatim in the text are silently skipped.
    """
    marks = []
    for r in reports or []:
        for iss in r.issues:
            marks.append((iss.quote, iss.severity.value, r.dimension, iss.problem))

    lowered = text.lower()
    spans = []  # (start, end, color, tooltip)
    for quote, sev, dim, problem in marks:
        q = (quote or "").lower()
        if not q:
            continue
        start = lowered.find(q)
        if start == -1:
            continue
        tip = f"[{dim} | {sev}] {problem}".replace('"', "'")
        spans.append((start, start + len(q), SEV_COLOR.get(sev, "#ffd43b"), tip))

    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    chosen, last_end = [], -1
    for s in spans:
        if s[0] >= last_end:
            chosen.append(s)
            last_end = s[1]

    out, cursor = [], 0
    for start, end, color, tip in chosen:
        out.append(esc(text[cursor:start]))
        out.append(
            f'<span title="{esc(tip)}" style="background:{color};color:#111;'
            f'border-radius:3px;padding:0 2px;cursor:help;">{esc(text[start:end])}</span>'
        )
        cursor = end
    out.append(esc(text[cursor:]))
    return "".join(out)
