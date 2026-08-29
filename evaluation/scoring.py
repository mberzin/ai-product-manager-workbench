"""Deterministic, wording-tolerant scoring for Phase 6 evaluations."""

from __future__ import annotations

from typing import Any

from evaluation.cases import EvaluationCase


def _normalize(value: str) -> str:
    """Normalize case, whitespace, and common Unicode dashes for fair matching."""
    for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        value = value.replace(dash, "-")
    for marker in ("*", "_", "`"):
        value = value.replace(marker, "")
    return " ".join(value.lower().split())


def _coverage(expected: set[str], observed: set[str]) -> float:
    return 1.0 if not expected else len(expected & observed) / len(expected)


def score_case(case: EvaluationCase, observation: dict[str, Any]) -> dict[str, Any]:
    specialists = set(observation.get("specialists", []))
    families = set(observation.get("tool_families", []))
    sources = set(observation.get("knowledge_sources", []))
    response = _normalize(str(observation.get("response", "")))

    required = set(case.expected_specialists)
    forbidden = set(case.normally_not_required)
    required_routing = _coverage(required, specialists)
    unnecessary = len(specialists & forbidden)
    routing_precision = 1.0 if not specialists else len(specialists & required) / len(specialists)

    evidence_results = []
    for requirement in case.required_evidence:
        text_ok = not requirement.response_any or any(
            _normalize(term) in response for term in requirement.response_any
        )
        tool_ok = not requirement.tool_families_any or bool(
            families & set(requirement.tool_families_any)
        )
        evidence_results.append({"id": requirement.id, "passed": text_ok and tool_ok})

    conclusion_results = [
        any(_normalize(term) in response for term in alternatives)
        for alternatives in case.conclusion_characteristics
    ]
    evidence_coverage = (
        sum(item["passed"] for item in evidence_results) / len(evidence_results)
        if evidence_results else 1.0
    )
    conclusion_coverage = (
        sum(conclusion_results) / len(conclusion_results)
        if conclusion_results else 1.0
    )
    source_coverage = _coverage(set(case.expected_knowledge_sources), sources)
    tool_coverage = _coverage(set(case.expected_tool_families), families)
    passed = all([
        required_routing == 1.0,
        unnecessary == 0,
        evidence_coverage == 1.0,
        source_coverage == 1.0,
        tool_coverage == 1.0,
        conclusion_coverage == 1.0,
        observation.get("error") is None,
    ])
    return {
        "passed": passed,
        "required_routing_coverage": round(required_routing, 4),
        "routing_precision": round(routing_precision, 4),
        "unnecessary_specialists": sorted(specialists & forbidden),
        "evidence_coverage": round(evidence_coverage, 4),
        "knowledge_source_coverage": round(source_coverage, 4),
        "tool_family_coverage": round(tool_coverage, 4),
        "conclusion_coverage": round(conclusion_coverage, 4),
        "evidence_checks": evidence_results,
    }
