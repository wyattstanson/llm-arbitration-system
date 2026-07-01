"""Live analytics over all stored arbitrations.

Everything here is computed from the SQLite audit trail on demand — nothing is
precomputed or hardcoded, so the numbers move as new arbitrations are recorded.
The headline question these answer: does multi-model critique actually catch things,
and which critic is pulling its weight vs. getting overruled?
"""

from __future__ import annotations

from collections import Counter
from typing import List, Optional

from src.storage.db import ArbitrationRecord, list_arbitrations

_DIMENSIONS = ("accuracy", "logic", "completeness")


def compute_analytics(records: Optional[List[ArbitrationRecord]] = None) -> dict:
    if records is None:
        records = list_arbitrations()

    total = len(records)
    if total == 0:
        return {"total_arbitrations": 0, "note": "No arbitrations recorded yet."}

    issues_by_critic = Counter()        # raw issues each critic raised
    confirmed_by_critic = Counter()     # issues each critic raised that were upheld
    overruled_by_critic = Counter()     # flags each critic raised that were dismissed
    disagreement_types = Counter()
    severity_of_confirmed = Counter()

    runs_with_disagreement = 0
    short_circuits = 0
    total_score = 0
    total_disagreements = 0

    for rec in records:
        v = rec.verdict
        total_score += v.overall_score
        total_disagreements += len(v.disagreements)
        if v.disagreements:
            runs_with_disagreement += 1
        if not v.adjudicated:
            short_circuits += 1

        for report in v.critic_reports:
            issues_by_critic[report.dimension] += len(report.issues)
        for ci in v.confirmed_issues:
            severity_of_confirmed[ci.severity.value] += 1
            for critic in ci.source_critics:
                confirmed_by_critic[critic] += 1
        for df in v.dismissed_flags:
            overruled_by_critic[df.raised_by] += 1
        for d in v.disagreements:
            disagreement_types[d.type] += 1

    def _avg_per_run(counter: Counter) -> dict:
        return {dim: round(counter.get(dim, 0) / total, 3) for dim in _DIMENSIONS}

    most_issues = max(_DIMENSIONS, key=lambda d: issues_by_critic.get(d, 0))
    most_overruled = (
        overruled_by_critic.most_common(1)[0][0] if overruled_by_critic else None
    )

    return {
        "total_arbitrations": total,
        "avg_overall_score": round(total_score / total, 2),
        "disagreement_rate": round(runs_with_disagreement / total, 3),
        "short_circuit_rate": round(short_circuits / total, 3),
        "avg_disagreements_per_run": round(total_disagreements / total, 3),
        "avg_issues_per_run_by_critic": _avg_per_run(issues_by_critic),
        "most_active_critic": most_issues,
        "confirmed_issues_by_critic": dict(confirmed_by_critic),
        "overruled_flags_by_critic": dict(overruled_by_critic),
        "most_overruled_critic": most_overruled,
        "disagreement_type_counts": dict(disagreement_types),
        "confirmed_issue_severity_distribution": dict(severity_of_confirmed),
    }
