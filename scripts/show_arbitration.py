"""Re-fetch a stored arbitration by ID and print it — demonstrates the audit trail.

Usage:
    python scripts/show_arbitration.py <id>
    python scripts/show_arbitration.py            # lists recent arbitrations
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.storage.db import get_arbitration, list_arbitrations  # noqa: E402


def main():
    if len(sys.argv) < 2:
        records = list_arbitrations(limit=20)
        if not records:
            print("No arbitrations stored yet. Run scripts/run_graph.py first.")
            return
        print(f"{'id':38}  {'created_at':26}  score  output excerpt")
        print("-" * 90)
        for r in records:
            excerpt = r.llm_output[:40].replace("\n", " ")
            print(f"{r.id:38}  {r.created_at:26}  {r.verdict.overall_score:>5}  {excerpt}")
        return

    rec = get_arbitration(sys.argv[1])
    if rec is None:
        print(f"No arbitration found with id {sys.argv[1]}")
        sys.exit(1)

    v = rec.verdict
    print(f"id          : {rec.id}")
    print(f"created_at  : {rec.created_at}")
    print(f"prompt      : {rec.original_prompt}")
    print(f"output      : {rec.llm_output[:200]}{'...' if len(rec.llm_output) > 200 else ''}")
    print(f"\nscore={v.overall_score}/10  confidence={v.confidence}  adjudicated={v.adjudicated}")
    print(f"summary: {v.summary}")
    print(f"\nconfirmed_issues : {len(v.confirmed_issues)}")
    print(f"dismissed_flags  : {len(v.dismissed_flags)}")
    print(f"disagreements    : {len(v.disagreements)}")
    print(f"critic_reports   : {len(v.critic_reports)}")


if __name__ == "__main__":
    main()
