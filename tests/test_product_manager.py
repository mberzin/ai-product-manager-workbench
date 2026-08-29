"""Lightweight tests that do not make an API request."""

import importlib.util
import unittest
from pathlib import Path


def load_product_manager_module():
    """Load the local module without colliding with the installed `agents` SDK."""
    module_path = Path(__file__).parents[1] / "agents" / "product_manager.py"
    spec = importlib.util.spec_from_file_location("product_manager", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load the agent definition at {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


product_manager_module = load_product_manager_module()
PRODUCT_MANAGER_INSTRUCTIONS = product_manager_module.PRODUCT_MANAGER_INSTRUCTIONS
product_manager_agent = product_manager_module.product_manager_agent
build_product_manager_agent = product_manager_module.build_product_manager_agent


class ProductManagerAgentTests(unittest.TestCase):
    def test_agent_has_expected_name(self) -> None:
        self.assertIn("Product Manager", product_manager_agent.name)

    def test_instructions_require_evidence_awareness(self) -> None:
        instructions = PRODUCT_MANAGER_INSTRUCTIONS.lower()
        self.assertIn("known facts", instructions)
        self.assertIn("assumptions", instructions)
        self.assertIn("insufficient data", instructions)
        self.assertIn("calculated facts", instructions)
        self.assertIn("do not claim a root cause", instructions)
        self.assertIn("retrieved facts", instructions)
        self.assertIn("use both file search", instructions)

    def test_agent_has_all_phase_three_tools(self) -> None:
        tool_names = {tool.name for tool in product_manager_agent.tools}
        analytical_tools = {
            "compare_model_versions", "calculate_precision", "calculate_recall",
            "calculate_false_positive_rate", "segment_model_performance",
            "analyze_complaint_trends", "segment_complaints",
            "identify_high_risk_customers", "analyze_latency_by_region",
            "analyze_uptime_by_customer", "analyze_feature_usage",
            "analyze_experiment", "compare_experiment_segments",
        }
        self.assertTrue(analytical_tools.issubset(tool_names))
        self.assertEqual(len(analytical_tools & tool_names), 13)

    def test_configured_agent_has_retrieval_and_analytical_tools(self) -> None:
        configured_agent = build_product_manager_agent("vs_test123")
        tool_names = {tool.name for tool in configured_agent.tools}
        self.assertEqual(len(tool_names), 14)
        self.assertIn("file_search", tool_names)
        self.assertIn("compare_model_versions", tool_names)
        file_search = next(tool for tool in configured_agent.tools if tool.name == "file_search")
        self.assertEqual(file_search.vector_store_ids, ["vs_test123"])
        self.assertEqual(file_search.max_num_results, 5)
        self.assertTrue(file_search.include_search_results)


if __name__ == "__main__":
    unittest.main()
