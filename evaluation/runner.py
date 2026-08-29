"""Live Phase 6 evaluation runner and aggregate reporting."""

from __future__ import annotations

import importlib.util
import json
import os
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

from agents import Runner

from evaluation.cases import EvaluationCase, load_cases
from evaluation.costs import estimate_cost
from evaluation.judge import judge_response
from evaluation.observability import (
    EvaluationHooks,
    cited_knowledge,
    specialist_names_from_events,
    usage_metadata,
)
from evaluation.scoring import score_case


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_RESULTS_DIR = Path(__file__).with_name("results")


def _load_builder():
    path = PROJECT_ROOT / "agents" / "product_manager.py"
    spec = importlib.util.spec_from_file_location("evaluation_product_manager", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load product manager agent from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_product_manager_agent


def run_case(
    case: EvaluationCase,
    judge: bool = False,
    pricing_model: str | None = None,
) -> dict:
    hooks = EvaluationHooks()
    agent = _load_builder()(specialist_hooks=hooks)
    started = time.perf_counter()
    result = None
    error = None
    try:
        result = Runner.run_sync(agent, case.question, hooks=hooks)
        response = str(result.final_output)
    except Exception as exc:  # Preserve the failed run as an evaluation result.
        message = str(exc)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            message = message.replace(api_key, "[REDACTED]")
        error = f"{type(exc).__name__}: {message}"
        response = ""
    latency = max(0.0, time.perf_counter() - started)
    hook_data = hooks.snapshot()
    events = hook_data["tool_events"]
    analytical_events = [event for event in events if event["family"] != "specialist_delegation"]
    specialists = specialist_names_from_events(events)
    knowledge = cited_knowledge(result) if result is not None else []
    usage = usage_metadata(result) if result is not None else None
    observation = {
        "response": response,
        "specialists": specialists,
        "knowledge_sources": knowledge,
        "tool_families": sorted({event["family"] for event in analytical_events}),
        "latency_seconds": round(latency, 4),
        "specialist_calls": sum(event["family"] == "specialist_delegation" for event in events),
        "analytical_tool_calls": len(analytical_events),
        # Hosted file-search calls are nested and not surfaced by local tool hooks.
        # Count retrieval-specialist invocations as an explicit, documented proxy.
        "retrieval_calls_proxy": sum(
            event["tool"] in {"consult_product_strategist", "consult_technical_pm"}
            for event in events
        ),
        "successful_tool_calls": hook_data["successful_tool_calls"],
        "failed_tool_calls": hook_data["failed_tool_calls"],
        "tool_events": events,
        "usage": usage,
        "cost": estimate_cost(usage, model=pricing_model),
        "error": error,
    }
    scored = score_case(case, observation)
    qualitative = None
    if judge and not error:
        qualitative = judge_response(
            case.question, response,
            [list(group) for group in case.conclusion_characteristics],
        )
    return {"case": asdict(case), "observation": observation,
            "scores": scored, "qualitative": qualitative}


def summarize(results: list[dict]) -> dict:
    total = len(results)
    if not total:
        raise ValueError("Cannot summarize an empty evaluation run")
    scores = [result["scores"] for result in results]
    observations = [result["observation"] for result in results]
    usage_rows = [row["usage"] for row in observations if row.get("usage")]
    unnecessary_calls = sum(len(score["unnecessary_specialists"]) for score in scores)
    specialist_calls = sum(row["specialist_calls"] for row in observations)
    summary = {
        "total_cases": total,
        "passed_cases": sum(score["passed"] for score in scores),
        "pass_rate": round(sum(score["passed"] for score in scores) / total, 4),
        "routing_accuracy": round(mean(score["required_routing_coverage"] for score in scores), 4),
        "routing_precision": round(mean(score["routing_precision"] for score in scores), 4),
        "unnecessary_delegation_rate": round(
            unnecessary_calls / specialist_calls if specialist_calls else 0.0, 4
        ),
        "evidence_coverage": round(mean(score["evidence_coverage"] for score in scores), 4),
        "knowledge_source_coverage": round(
            mean(score["knowledge_source_coverage"] for score in scores), 4
        ),
        "tool_family_coverage": round(mean(score["tool_family_coverage"] for score in scores), 4),
        "average_latency_seconds": round(mean(row["latency_seconds"] for row in observations), 4),
        "average_specialist_calls": round(mean(row["specialist_calls"] for row in observations), 4),
        "average_analytical_tool_calls": round(
            mean(row["analytical_tool_calls"] for row in observations), 4
        ),
        "average_retrieval_calls_proxy": round(
            mean(row["retrieval_calls_proxy"] for row in observations), 4
        ),
        "successful_tool_calls": sum(row["successful_tool_calls"] for row in observations),
        "failed_tool_calls": sum(row["failed_tool_calls"] for row in observations),
        "token_usage": {
            "available_cases": len(usage_rows),
            "input_tokens": sum(row["input_tokens"] for row in usage_rows),
            "output_tokens": sum(row["output_tokens"] for row in usage_rows),
            "total_tokens": sum(row["total_tokens"] for row in usage_rows),
        },
        "cost_estimate": "unavailable until explicit model pricing is configured",
        "failed_case_ids": [
            result["case"]["id"] for result in results if not result["scores"]["passed"]
        ],
    }
    judge_rows = [result["qualitative"] for result in results
                  if result.get("qualitative") and result["qualitative"].get("available")]
    if judge_rows:
        dimensions = ["recommendation_quality", "appropriate_uncertainty",
                      "avoids_unsupported_causality", "evidence_synthesis", "pm_judgment"]
        summary["qualitative_scores"] = {
            dimension: round(mean(float(row[dimension]) for row in judge_rows), 2)
            for dimension in dimensions if all(dimension in row for row in judge_rows)
        }
        summary["qualitative_label"] = "model-based evaluation"
    return summary


def save_results(results: list[dict], summary: dict, directory: Path = DEFAULT_RESULTS_DIR) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = directory / f"evaluation_{stamp}.json"
    markdown_path = directory / f"evaluation_{stamp}.md"
    payload = {"generated_at": datetime.now(UTC).isoformat(), "summary": summary,
               "results": results}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# Evaluation summary", ""]
    for key, value in summary.items():
        lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


def select_cases(case_id: str | None) -> list[EvaluationCase]:
    cases = load_cases()
    if case_id is None:
        return cases
    matches = [case for case in cases if case.id == case_id]
    if not matches:
        raise ValueError(f"Unknown evaluation case '{case_id}'")
    return matches
