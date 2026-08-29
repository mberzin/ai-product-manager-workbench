"""Deterministic tests for Phase 6 evaluation and observability."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evaluation.cases import VALID_MODES, VALID_SPECIALISTS, load_cases
from evaluation.costs import PRICING_PATH, estimate_cost
from evaluation.ground_truth import GROUND_TRUTH_PATH, load_evaluation_ground_truth
from evaluation.observability import EvaluationHooks, usage_metadata
from evaluation.scoring import score_case


PROJECT_ROOT = Path(__file__).parents[1]


class EvaluationCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_cases()

    def test_case_dataset_has_valid_schema_and_expected_size(self) -> None:
        self.assertGreaterEqual(len(self.cases), 10)
        self.assertLessEqual(len(self.cases), 15)
        self.assertEqual(len({case.id for case in self.cases}), len(self.cases))
        for case in self.cases:
            with self.subTest(case=case.id):
                self.assertTrue(case.question)
                self.assertIn(case.mode, VALID_MODES)
                self.assertTrue(set(case.expected_specialists).issubset(VALID_SPECIALISTS))
                self.assertTrue(set(case.normally_not_required).issubset(VALID_SPECIALISTS))
                self.assertTrue(case.required_evidence)
                self.assertTrue(case.known_uncertainties)

    def test_complaint_spike_routing_matches_quantitative_diagnosis_policy(self) -> None:
        case = {case.id: case for case in self.cases}["v32_complaint_spike"]
        self.assertEqual(case.expected_specialists, ("Data Analyst",))
        self.assertEqual(
            set(case.normally_not_required),
            {"Product Strategist", "Technical Product Manager"},
        )
        self.assertEqual(case.expected_tool_families, ("complaints", "model_performance"))
        self.assertEqual(case.expected_knowledge_sources, ())
        self.assertEqual(case.mode, "quantitative")
        self.assertTrue(case.required_evidence)
        self.assertTrue(case.conclusion_characteristics)
        self.assertTrue(case.known_uncertainties)

    def test_evaluation_code_can_access_ground_truth(self) -> None:
        text = load_evaluation_ground_truth()
        self.assertEqual(GROUND_TRUTH_PATH.parent, PROJECT_ROOT / "data")
        self.assertIn("Scenario A", text)
        self.assertIn("Scenario F", text)

    def test_ground_truth_access_is_isolated_from_production(self) -> None:
        forbidden = "ground" + "_truth"
        production_paths = [PROJECT_ROOT / "app.py"]
        for directory in ["agents", "rag", "tools"]:
            production_paths.extend((PROJECT_ROOT / directory).glob("*.py"))
        for path in production_paths:
            with self.subTest(path=path):
                self.assertNotIn(forbidden, path.read_text(encoding="utf-8").lower())


class DeterministicScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.latency_case = {case.id: case for case in load_cases()}["eu_latency_regression"]

    def observation(self, **overrides):
        value = {
            "response": "EU-specific latency regression increased; non-EU stayed flat. p95 rose. Root cause is unknown.",
            "specialists": ["Data Analyst"],
            "knowledge_sources": [],
            "tool_families": ["latency"],
            "error": None,
        }
        value.update(overrides)
        return value

    def test_routing_and_evidence_scoring_pass(self) -> None:
        scores = score_case(self.latency_case, self.observation())
        self.assertTrue(scores["passed"])
        self.assertEqual(scores["required_routing_coverage"], 1.0)
        self.assertEqual(scores["evidence_coverage"], 1.0)

    def test_scoring_tolerates_markdown_emphasis_and_unicode_dashes(self) -> None:
        observation = self.observation(
            response=(
                "EU latency **regressed** and appears EU‑specific; non-EU stayed flat. "
                "p95 rose, but the data does **not** identify the cause."
            )
        )
        self.assertTrue(score_case(self.latency_case, observation)["passed"])

    def test_unnecessary_delegation_is_detected(self) -> None:
        scores = score_case(
            self.latency_case,
            self.observation(specialists=["Data Analyst", "Product Strategist"]),
        )
        self.assertFalse(scores["passed"])
        self.assertEqual(scores["unnecessary_specialists"], ["Product Strategist"])
        self.assertEqual(scores["routing_precision"], 0.5)

    def test_missing_evidence_and_tool_family_are_detected(self) -> None:
        scores = score_case(
            self.latency_case,
            self.observation(response="Latency was different.", tool_families=[]),
        )
        self.assertFalse(scores["passed"])
        self.assertLess(scores["evidence_coverage"], 1.0)
        self.assertEqual(scores["tool_family_coverage"], 0.0)


class ObservabilityTests(unittest.TestCase):
    def test_latency_and_tool_metadata_are_valid(self) -> None:
        hooks = EvaluationHooks()
        agent = SimpleNamespace(name="Data Analyst")
        tool = SimpleNamespace(name="analyze_latency_by_region")

        async def exercise_hooks():
            await hooks.on_agent_start(None, agent)
            await hooks.on_tool_start(None, agent, tool)
            await hooks.on_tool_end(None, agent, tool, "ok")

        asyncio.run(exercise_hooks())
        snapshot = hooks.snapshot()
        event = snapshot["tool_events"][0]
        self.assertEqual(event["family"], "latency")
        self.assertTrue(event["success"])
        self.assertGreaterEqual(event["duration_seconds"], 0.0)
        self.assertEqual(snapshot["failed_tool_calls"], 0)

    def test_actual_usage_metadata_is_read_without_fabrication(self) -> None:
        usage = SimpleNamespace(requests=3, input_tokens=100, output_tokens=25, total_tokens=125)
        result = SimpleNamespace(context_wrapper=SimpleNamespace(usage=usage))
        self.assertEqual(usage_metadata(result)["total_tokens"], 125)
        self.assertIsNone(usage_metadata(SimpleNamespace(context_wrapper=None)))

    def test_cost_uses_one_explicit_pricing_configuration(self) -> None:
        self.assertEqual(PRICING_PATH.parent, PROJECT_ROOT / "evaluation")
        config = {
            "currency": "USD",
            "per_million_tokens": {"test-model": {"input": 2.0, "output": 8.0}},
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "pricing.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            estimate = estimate_cost(
                {"input_tokens": 1_000_000, "output_tokens": 500_000},
                "test-model",
                path,
            )
        self.assertTrue(estimate["available"])
        self.assertEqual(estimate["estimated_cost"], 6.0)
        self.assertFalse(estimate_cost({"input_tokens": 1, "output_tokens": 1}, None)["available"])


if __name__ == "__main__":
    unittest.main()
