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


class ProductManagerAgentTests(unittest.TestCase):
    def test_agent_has_expected_name(self) -> None:
        self.assertIn("Product Manager", product_manager_agent.name)

    def test_instructions_require_evidence_awareness(self) -> None:
        instructions = PRODUCT_MANAGER_INSTRUCTIONS.lower()
        self.assertIn("known facts", instructions)
        self.assertIn("assumptions", instructions)
        self.assertIn("insufficient data", instructions)
        self.assertIn("tool-derived facts", instructions)
        self.assertIn("do not claim a root cause", instructions)

    def test_agent_has_all_phase_three_tools(self) -> None:
        tool_names = {tool.name for tool in product_manager_agent.tools}
        self.assertEqual(
            tool_names,
            {
                "compare_model_versions", "calculate_precision", "calculate_recall",
                "calculate_false_positive_rate", "segment_model_performance",
                "analyze_complaint_trends", "segment_complaints",
                "identify_high_risk_customers", "analyze_latency_by_region",
                "analyze_uptime_by_customer", "analyze_feature_usage",
                "analyze_experiment", "compare_experiment_segments",
            },
        )


if __name__ == "__main__":
    unittest.main()
