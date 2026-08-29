"""Shared, read-only access helpers for the synthetic CallGuard AI CSVs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Production tools can read only these explicitly listed synthetic CSVs. No caller
# can provide a filename or path, so developer-only artifacts are unreachable.
ALLOWED_DATASETS = {
    "calls.csv",
    "customers.csv",
    "experiments.csv",
    "model_versions.csv",
    "product_usage.csv",
    "support_tickets.csv",
}


@lru_cache(maxsize=len(ALLOWED_DATASETS))
def _cached_csv(filename: str) -> pd.DataFrame:
    if filename not in ALLOWED_DATASETS:
        raise ValueError(f"Dataset is not available to analytical tools: {filename}")
    return pd.read_csv(DATA_DIR / filename)


def load_data(filename: str) -> pd.DataFrame:
    """Return a defensive copy so one analysis cannot mutate cached source data."""
    return _cached_csv(filename).copy()


def add_region(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the dataset's explicit analytical region mapping."""
    eu_countries = {"Germany", "France", "Ireland", "Netherlands", "Spain"}
    result = frame.copy()
    result["region"] = result["country"].where(result["country"].isin(eu_countries), "Non-EU")
    result.loc[result["country"].isin(eu_countries), "region"] = "EU"
    return result


def date_filter(
    frame: pd.DataFrame,
    column: str,
    start_date: str | None,
    end_date: str | None,
) -> tuple[pd.DataFrame, str | None]:
    """Apply inclusive ISO date filters and return an error instead of raising."""
    result = frame.copy()
    result[column] = pd.to_datetime(result[column])
    try:
        if start_date:
            result = result[result[column] >= pd.Timestamp(start_date)]
        if end_date:
            result = result[result[column] <= pd.Timestamp(end_date)]
    except (TypeError, ValueError):
        return result.iloc[0:0], "Dates must use ISO format, for example 2025-09-01."
    if start_date and end_date and pd.Timestamp(start_date) > pd.Timestamp(end_date):
        return result.iloc[0:0], "start_date must be on or before end_date."
    return result, None


def time_period(frame: pd.DataFrame, column: str) -> dict[str, str | None]:
    if frame.empty:
        return {"start": None, "end": None}
    dates = pd.to_datetime(frame[column])
    return {"start": dates.min().date().isoformat(), "end": dates.max().date().isoformat()}


def to_json(payload: dict[str, Any]) -> str:
    """Serialize compact tool output, including pandas/numpy scalar values."""
    def convert(value: Any) -> Any:
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            return value.item()
        return str(value)

    return json.dumps(payload, default=convert, separators=(",", ":"))


def error_result(message: str, **context: Any) -> str:
    return to_json({"status": "error", "message": message, **context})


def bounded_limit(limit: int, maximum: int = 20) -> int:
    """Keep model-requested result sizes useful and safe."""
    return max(1, min(limit, maximum))
