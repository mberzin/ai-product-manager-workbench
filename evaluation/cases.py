"""Load and validate the structured Phase 6 evaluation cases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


CASES_PATH = Path(__file__).with_name("cases.json")
VALID_SPECIALISTS = {
    "Data Analyst", "Product Strategist", "Technical Product Manager"
}
VALID_MODES = {"quantitative", "retrieval", "both"}


@dataclass(frozen=True)
class EvidenceRequirement:
    id: str
    response_any: tuple[str, ...] = ()
    tool_families_any: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    question: str
    category: str
    expected_specialists: tuple[str, ...]
    normally_not_required: tuple[str, ...]
    required_evidence: tuple[EvidenceRequirement, ...]
    expected_knowledge_sources: tuple[str, ...]
    expected_tool_families: tuple[str, ...]
    conclusion_characteristics: tuple[tuple[str, ...], ...]
    known_uncertainties: tuple[str, ...]
    mode: str


def _nonempty_strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return tuple(value)


def _parse_case(raw: dict) -> EvaluationCase:
    required = {"id", "question", "category", "expected_specialists",
                "normally_not_required", "required_evidence",
                "expected_knowledge_sources", "expected_tool_families",
                "conclusion_characteristics", "known_uncertainties", "mode"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"Evaluation case is missing fields: {sorted(missing)}")
    specialists = _nonempty_strings(raw["expected_specialists"], "expected_specialists")
    not_required = _nonempty_strings(raw["normally_not_required"], "normally_not_required")
    if (set(specialists) | set(not_required)) - VALID_SPECIALISTS:
        raise ValueError(f"Unknown specialist in case {raw['id']}")
    if set(specialists) & set(not_required):
        raise ValueError(f"A specialist cannot be required and unnecessary in case {raw['id']}")
    if raw["mode"] not in VALID_MODES:
        raise ValueError(f"Invalid mode in case {raw['id']}")

    evidence = []
    for item in raw["required_evidence"]:
        if not isinstance(item, dict) or not item.get("id"):
            raise ValueError(f"Invalid evidence requirement in case {raw['id']}")
        evidence.append(EvidenceRequirement(
            id=item["id"],
            response_any=_nonempty_strings(item.get("response_any", []), "response_any"),
            tool_families_any=_nonempty_strings(
                item.get("tool_families_any", []), "tool_families_any"
            ),
        ))
    characteristics = tuple(
        _nonempty_strings(group, "conclusion_characteristics")
        for group in raw["conclusion_characteristics"]
    )
    return EvaluationCase(
        id=raw["id"], question=raw["question"], category=raw["category"],
        expected_specialists=specialists, normally_not_required=not_required,
        required_evidence=tuple(evidence),
        expected_knowledge_sources=_nonempty_strings(
            raw["expected_knowledge_sources"], "expected_knowledge_sources"
        ),
        expected_tool_families=_nonempty_strings(
            raw["expected_tool_families"], "expected_tool_families"
        ),
        conclusion_characteristics=characteristics,
        known_uncertainties=_nonempty_strings(raw["known_uncertainties"], "known_uncertainties"),
        mode=raw["mode"],
    )


def load_cases(path: Path = CASES_PATH) -> list[EvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        raise ValueError("Evaluation dataset must be a JSON array")
    cases = [_parse_case(raw) for raw in raw_cases]
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation case IDs must be unique")
    return cases
