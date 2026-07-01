"""Manual smoke test: run all three critics on one input and print their reports.

Usage:
    python scripts/run_critics.py                      # default: factually_incorrect fixture
    python scripts/run_critics.py logically_flawed     # any fixture name in tests/fixtures
    python scripts/run_critics.py --text "some output" [--prompt "the question"]
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running as a plain script (python scripts/run_critics.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.critics import AccuracyCritic, CompletenessCritic, LogicCritic  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def load_fixture(name: str):
    path = FIXTURES / (name if name.endswith(".json") else f"{name}.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["llm_output"], data.get("original_prompt")


def print_report(label, report, elapsed):
    if report is None:
        print(f"\n### {label}: FAILED (see error above)")
        return
    print(f"\n### {label}  [{report.critic_model}]  score={report.score}/5  "
          f"confidence={report.confidence:.2f}  ({elapsed:.1f}s)")
    if not report.issues:
        print("   (no issues found)")
    for i, iss in enumerate(report.issues, 1):
        print(f"   {i}. [{iss.severity.value.upper()}] {iss.problem}")
        print(f'      quote: "{iss.quote}"')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", nargs="?", default="factually_incorrect")
    ap.add_argument("--text")
    ap.add_argument("--prompt")
    args = ap.parse_args()

    if args.text:
        llm_output, original_prompt = args.text, args.prompt
        source = "inline text"
    else:
        llm_output, original_prompt = load_fixture(args.fixture)
        source = f"fixture: {args.fixture}"

    print("=" * 70)
    print(f"Providers this run: {json.dumps(config.provider_summary(), indent=2)}")
    print(f"Input: {source}")
    print(f"Prompt: {original_prompt}")
    print("=" * 70)

    critics = [
        ("ACCURACY", AccuracyCritic()),
        ("LOGIC", LogicCritic()),
        ("COMPLETENESS", CompletenessCritic()),
    ]
    for label, critic in critics:
        t0 = time.time()
        try:
            report = critic.critique(llm_output, original_prompt)
            print_report(label, report, time.time() - t0)
        except Exception as e:  # noqa: BLE001
            print(f"\n### {label}: ERROR -> {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
