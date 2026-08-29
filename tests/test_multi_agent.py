"""Deterministic construction and least-privilege tests for Phase 5 agents."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from rag.config import KNOWLEDGE_FILES


PROJECT_ROOT = Path(__file__).parents[1]
AGENTS_DIR = PROJECT_ROOT / "agents"
ANALYTICAL_TOOL_NAMES = {
    "compare_model_versions", "calculate_precision", "calculate_recall",
    "calculate_false_positive_rate", "segment_model_performance",
    "analyze_complaint_trends", "segment_complaints", "identify_high_risk_customers",
    "analyze_latency_by_region", "analyze_uptime_by_customer",
    "analyze_feature_usage", "analyze_experiment", "compare_experiment_segments",
}


def load_local_agent_module(filename: str):
    path = AGENTS_DIR / filename
    spec = importlib.util.spec_from_file_location(f"test_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MultiAgentConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data_module = load_local_agent_module("data_analyst.py")
        cls.strategy_module = load_local_agent_module("product_strategist.py")
        cls.technical_module = load_local_agent_module("technical_pm.py")
        cls.orchestrator_module = load_local_agent_module("product_manager.py")

    def test_all_four_agents_construct(self) -> None:
        self.assertEqual(self.data_module.build_data_analyst_agent().name, "Data Analyst")
        self.assertEqual(
            self.strategy_module.build_product_strategist_agent("vs_test123").name,
            "Product Strategist",
        )
        self.assertEqual(
            self.technical_module.build_technical_pm_agent("vs_test123").name,
            "Technical Product Manager",
        )
        self.assertEqual(
            self.orchestrator_module.build_product_manager_agent("vs_test123").name,
            "Product Manager Orchestrator",
        )

    def test_data_analyst_has_all_analytical_tools_and_no_retrieval(self) -> None:
        agent = self.data_module.build_data_analyst_agent()
        self.assertEqual({tool.name for tool in agent.tools}, ANALYTICAL_TOOL_NAMES)
        self.assertNotIn("file_search", {tool.name for tool in agent.tools})

    def test_product_strategist_has_restricted_retrieval_only(self) -> None:
        agent = self.strategy_module.build_product_strategist_agent("vs_test123")
        self.assertEqual([tool.name for tool in agent.tools], ["file_search"])
        file_search = agent.tools[0]
        self.assertEqual(set(file_search.filters["value"]), set(self.strategy_module.STRATEGY_KNOWLEDGE_FILES))
        self.assertTrue(set(file_search.filters["value"]).issubset(KNOWLEDGE_FILES))

    def test_technical_pm_has_restricted_retrieval_only(self) -> None:
        agent = self.technical_module.build_technical_pm_agent("vs_test123")
        self.assertEqual([tool.name for tool in agent.tools], ["file_search"])
        file_search = agent.tools[0]
        self.assertEqual(set(file_search.filters["value"]), set(self.technical_module.TECHNICAL_KNOWLEDGE_FILES))
        self.assertTrue(set(file_search.filters["value"]).issubset(KNOWLEDGE_FILES))

    def test_orchestrator_can_delegate_to_each_specialist(self) -> None:
        agent = self.orchestrator_module.build_product_manager_agent("vs_test123")
        self.assertEqual(
            {tool.name for tool in agent.tools},
            {"consult_data_analyst", "consult_product_strategist", "consult_technical_pm"},
        )

    def test_data_analyst_instructions_require_time_aware_change_analysis(self) -> None:
        instructions = " ".join(self.data_module.DATA_ANALYST_INSTRUCTIONS.lower().split())
        for phrase in ["what happened", "regression", "time period", "bounded date windows"]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, instructions)
        self.assertIn("do not stop at an all-time aggregate", instructions)
        self.assertIn("successive narrower calendar windows", instructions)
        self.assertIn("monthly where feasible", instructions)
        self.assertIn("never assume a release or incident date", instructions)

    def test_orchestrator_keeps_descriptive_knowledge_routing_specialized(self) -> None:
        instructions = " ".join(
            self.orchestrator_module.PRODUCT_MANAGER_INSTRUCTIONS.lower().split()
        )
        self.assertIn("purely descriptive company or product knowledge", instructions)
        self.assertIn("consult only the product strategist", instructions)
        self.assertIn("do not consult the data analyst merely", instructions)

        agent = self.orchestrator_module.build_product_manager_agent("vs_test123")
        descriptions = {tool.name: tool.description.lower() for tool in agent.tools}
        self.assertIn("do not use for purely descriptive", descriptions["consult_data_analyst"])
        self.assertIn("use this specialist alone", descriptions["consult_product_strategist"])

    def test_orchestrator_routes_by_intent_and_minimum_sufficient_team(self) -> None:
        instructions = " ".join(
            self.orchestrator_module.PRODUCT_MANAGER_INSTRUCTIONS.lower().split()
        )
        for phrase in [
            "route by the user's requested outcome",
            "quantitative diagnosis or prioritization",
            "data analyst + product strategist are normally sufficient",
            "does not by itself require the technical product manager",
            "do not invoke a specialist simply because it could add interesting context",
            "use all three only when",
            "distinguish diagnosis from decision-making",
            "product rollout posture is a strategic decision",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, instructions)

        agent = self.orchestrator_module.build_product_manager_agent("vs_test123")
        descriptions = {tool.name: tool.description.lower() for tool in agent.tools}
        self.assertIn("account prioritization based on arr", descriptions["consult_data_analyst"])
        self.assertIn("do not use for account ranking", descriptions["consult_product_strategist"])
        self.assertIn("company-level product decisions", descriptions["consult_product_strategist"])
        self.assertIn("topic alone is not sufficient", descriptions["consult_technical_pm"])

    def test_specialists_do_not_expose_forbidden_file_or_path_parameters(self) -> None:
        strategist = self.strategy_module.build_product_strategist_agent("vs_test123")
        technical = self.technical_module.build_technical_pm_agent("vs_test123")
        for agent in [strategist, technical]:
            with self.subTest(agent=agent.name):
                serialized_filter = str(agent.tools[0].filters).lower()
                self.assertNotIn("ground" + "_truth", serialized_filter)
                self.assertNotIn(".csv", serialized_filter)


if __name__ == "__main__":
    unittest.main()
