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


if __name__ == "__main__":
    unittest.main()
