"""Disagreement detector — the signal-extraction core of the system.

Given the three critic reports, find where they genuinely conflict. Disagreement
is the *signal* this whole architecture exists to surface, so the rules are
implemented explicitly rather than averaged away.

Three rule types (from the spec), and how this module disambiguates them so every
detected conflict maps to exactly one type:

  severity_gap      Two critics flag the SAME region but rate it >2 severity levels
                    apart (rank map low=1, medium=3, high=5 -> only low-vs-high,
                    a gap of 4, qualifies).

  presence_mismatch One critic flags a region NO other critic mentions, AND those
                    other critics scored their own dimension HIGH (>=4) — i.e. they
                    were confident the output was clean exactly where this critic
                    found a problem. The high-confidence contradiction is the point.

  unique_find       One critic flags a region no other critic mentions, but the
                    "others were confident" condition does NOT hold — a category
                    simply nobody else caught.

Two issues are treated as the "same region" when their quotes overlap textually
(substring containment or token-Jaccard above threshold), since different critics
rarely copy the exact same substring for the same underlying problem.
"""

from __future__ import annotations

import re
from itertools import combinations
from typing import List, Optional

from src.schemas.critique import SEVERITY_RANK, CritiqueReport, Issue
from src.schemas.verdict import Disagreement

# Tunables (documented assumptions — see status report).
HIGH_SCORE_THRESHOLD = 4  # a critic "scored its dimension highly" at >= this
SEVERITY_GAP_THRESHOLD = 2  # rank difference must EXCEED this to count as a gap
JACCARD_THRESHOLD = 0.5  # token overlap above which two quotes are the "same region"

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _same_region(a: str, b: str) -> bool:
    """True if two quotes plausibly refer to the same span of the output."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    jaccard = len(ta & tb) / len(ta | tb)
    return jaccard >= JACCARD_THRESHOLD


class _Flag:
    """An issue paired with the critic (dimension) that raised it."""

    __slots__ = ("dimension", "issue")

    def __init__(self, dimension: str, issue: Issue):
        self.dimension = dimension
        self.issue = issue


def detect_disagreements(reports: List[Optional[CritiqueReport]]) -> List[Disagreement]:
    """Compare critic reports and return every conflict found."""
    present = [r for r in reports if r is not None]
    flags = [_Flag(r.dimension, iss) for r in present for iss in r.issues]
    disagreements: List[Disagreement] = []

    # --- severity_gap: same region, >2 severity levels apart -----------------
    paired_region_indices: set[int] = set()
    for (i, fa), (j, fb) in combinations(enumerate(flags), 2):
        if fa.dimension == fb.dimension:
            continue
        if not _same_region(fa.issue.quote, fb.issue.quote):
            continue
        # Both critics agree there's an issue here -> mark as paired (so it can't
        # later be mistaken for a unique catch), and check the severity spread.
        paired_region_indices.add(i)
        paired_region_indices.add(j)
        gap = abs(SEVERITY_RANK[fa.issue.severity] - SEVERITY_RANK[fb.issue.severity])
        if gap > SEVERITY_GAP_THRESHOLD:
            disagreements.append(
                Disagreement(
                    type="severity_gap",
                    description=(
                        f"{fa.dimension} and {fb.dimension} critics both flagged the same text "
                        f"but disagree sharply on how serious it is "
                        f"({fa.issue.severity.value} vs {fb.issue.severity.value})."
                    ),
                    critics_involved=sorted({fa.dimension, fb.dimension}),
                    details=(
                        f'Region: "{fa.issue.quote}"\n'
                        f"- {fa.dimension}: {fa.issue.severity.value} — {fa.issue.problem}\n"
                        f"- {fb.dimension}: {fb.issue.severity.value} — {fb.issue.problem}"
                    ),
                )
            )

    # --- unique catches: a region only ONE critic flagged --------------------
    for idx, flag in enumerate(flags):
        if idx in paired_region_indices:
            continue  # another critic flagged this same region -> not unique

        others = [r for r in present if r.dimension != flag.dimension]
        # Did the other critics score their own dimension highly (confident-clean)?
        others_confident = bool(others) and all(
            r.score >= HIGH_SCORE_THRESHOLD for r in others
        )

        if others_confident:
            disagreements.append(
                Disagreement(
                    type="presence_mismatch",
                    description=(
                        f"{flag.dimension} critic flagged an issue the other critics did not "
                        f"mention at all, even though they scored their own dimensions highly."
                    ),
                    critics_involved=sorted(
                        {flag.dimension} | {r.dimension for r in others}
                    ),
                    details=(
                        f'Only {flag.dimension} flagged: "{flag.issue.quote}" '
                        f"({flag.issue.severity.value}) — {flag.issue.problem}. "
                        f"Other critics' scores: "
                        + ", ".join(f"{r.dimension}={r.score}" for r in others)
                    ),
                )
            )
        else:
            disagreements.append(
                Disagreement(
                    type="unique_find",
                    description=(
                        f"{flag.dimension} critic surfaced an issue category none of the other "
                        f"critics detected in any form."
                    ),
                    critics_involved=[flag.dimension],
                    details=(
                        f'Unique to {flag.dimension}: "{flag.issue.quote}" '
                        f"({flag.issue.severity.value}) — {flag.issue.problem}."
                    ),
                )
            )

    return disagreements
