"""Explicit evaluation-only access to the developer ground-truth document."""

from pathlib import Path


GROUND_TRUTH_PATH = Path(__file__).parents[1] / "data" / "ground_truth.md"


def load_evaluation_ground_truth() -> str:
    """Read ground truth for evaluator development; never import from production."""
    return GROUND_TRUTH_PATH.read_text(encoding="utf-8")
