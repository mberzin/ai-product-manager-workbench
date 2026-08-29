"""Optional cost estimation from one explicit, user-maintained pricing table."""

from __future__ import annotations

import json
from pathlib import Path


PRICING_PATH = Path(__file__).with_name("pricing.json")


def estimate_cost(usage: dict | None, model: str | None, path: Path = PRICING_PATH) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    rates = config.get("per_million_tokens", {}).get(model or "")
    if not usage or not rates:
        return {"available": False, "estimated_cost": None, "currency": config["currency"]}
    estimate = (
        usage["input_tokens"] * rates["input"]
        + usage["output_tokens"] * rates["output"]
    ) / 1_000_000
    return {"available": True, "estimated_cost": round(estimate, 6),
            "currency": config["currency"], "model": model}
