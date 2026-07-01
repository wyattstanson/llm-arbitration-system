"""Run the full arbitration graph end-to-end on a fixture (or inline text) and
print the resulting Verdict.

Usage:
    python scripts/run_graph.py                    # default: factually_incorrect
    python scripts/run_graph.py genuinely_good     # any fixture name
    python scripts/run_graph.py --text "..." [--prompt "..."]
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.graph.build_graph import run_arbitration  # noqa: E402
from src.storage.db import save_arbitration  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def load_fixture(name: str):
    path = FIXTURES / (name if name.endswith(".json") else f"{name}.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["llm_output"], data.get("original_prompt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", nargs="?", default="factually_incorrect")
    ap.add_argument("--text")
    ap.add_argument("--prompt")
    ap.add_argument("--no-save", action="store_true", help="skip persisting to SQLite")
    args = ap.parse_args()

    if args.text:
        llm_output, original_prompt = args.text, args.prompt
    else:
        llm_output, original_prompt = load_fixture(args.fixture)

    print("=" * 72)
    print(f"Providers: {json.dumps(config.provider_summary())}")
    print(f"Input: {args.text and 'inline text' or args.fixture}")
    print("=" * 72)

    t0 = time.time()
    state = run_arbitration(llm_output, original_prompt)
    elapsed = time.time() - t0
    v = state["verdict"]

    print(f"\nFinished in {elapsed:.1f}s")
    print(f"failed_critics: {state['failed_critics']}")
    print(f"\n{'='*72}\nVERDICT\n{'='*72}")
    print(f"overall_score : {v.overall_score}/10")
    print(f"confidence    : {v.confidence}")
    print(f"adjudicated   : {v.adjudicated}  (False = unanimous-pass short-circuit)")
    print(f"\nsummary: {v.summary}")

    print(f"\n--- disagreements ({len(v.disagreements)}) ---")
    for d in v.disagreements:
        print(f"  [{d.type}] {d.description}")

    print(f"\n--- confirmed issues ({len(v.confirmed_issues)}) ---")
    for c in v.confirmed_issues:
        print(f"  [{c.severity.value}] {c.description}  (from: {', '.join(c.source_critics)})")

    print(f"\n--- dismissed flags ({len(v.dismissed_flags)}) ---")
    for f in v.dismissed_flags:
        print(f"  raised_by={f.raised_by}: {f.description}\n    reason: {f.reasoning}")

    if not args.no_save:
        rec = save_arbitration(llm_output, original_prompt, v)
        print(f"\nPersisted to SQLite. id = {rec.id}")
        print(f"Re-fetch with: python scripts/show_arbitration.py {rec.id}")


if __name__ == "__main__":
    main()
