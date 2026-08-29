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
        self.assertIn("calculated evidence", instructions)
        self.assertIn("retrieved knowledge", instructions)
        self.assertIn("hypotheses", instructions)
        self.assertIn("do not claim causality", instructions)
        self.assertIn("never call all specialists by default", instructions)

    def test_orchestrator_has_only_specialist_delegation_tools(self) -> None:
        tool_names = {tool.name for tool in product_manager_agent.tools}
        self.assertEqual(
            tool_names,
            {
                "consult_data_analyst",
                "consult_product_strategist",
                "consult_technical_pm",
            },
        )

    def test_orchestrator_can_be_built_with_configured_retrieval(self) -> None:
        configured_agent = build_product_manager_agent("vs_test123")
        self.assertEqual(configured_agent.name, "Product Manager Orchestrator")
        self.assertEqual(
            {tool.name for tool in configured_agent.tools},
            {
                "consult_data_analyst",
                "consult_product_strategist",
                "consult_technical_pm",
            },
        )


if __name__ == "__main__":
    unittest.main()
