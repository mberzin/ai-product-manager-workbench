"""CLI for the separated Phase 6 evaluation framework."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.runner import run_case, save_results, select_cases, summarize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 6 evaluations")
    parser.add_argument("--case", help="Run one case ID; omit to run all cases")
    parser.add_argument("--judge", action="store_true", help="Enable optional model-based judging")
    parser.add_argument(
        "--pricing-model",
        help="Pricing-table model key used only for clearly labeled cost estimates",
    )
    parser.add_argument("--results-dir", type=Path, help="Override the local results directory")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Live evaluations skipped: OPENAI_API_KEY is unavailable.")
        return 0
    cases = select_cases(args.case)
    results = []
    for index, case in enumerate(cases, 1):
        print(f"[{index}/{len(cases)}] {case.id}: {case.question}")
        result = run_case(case, judge=args.judge, pricing_model=args.pricing_model)
        results.append(result)
        status = "PASS" if result["scores"]["passed"] else "WEAK/FAIL"
        print(f"  {status} | {result['observation']['latency_seconds']:.2f}s | "
              f"specialists={result['observation']['specialists']}")
    summary = summarize(results)
    paths = save_results(results, summary, args.results_dir) if args.results_dir else save_results(results, summary)
    print(json.dumps(summary, indent=2))
    print(f"Saved JSON: {paths[0]}")
    print(f"Saved summary: {paths[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
