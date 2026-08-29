"""Safety and configuration tests for the Phase 4 retrieval boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rag.config import (
    CONFIG_PATH,
    KNOWLEDGE_DIR,
    KNOWLEDGE_FILES,
    VECTOR_STORE_NAME,
    default_config,
    is_valid_vector_store_id,
    knowledge_paths,
    load_config,
    validate_config,
)


PROJECT_ROOT = Path(__file__).parents[1]


class RagConfigurationTests(unittest.TestCase):
    def test_allowlist_contains_only_expected_knowledge_files(self) -> None:
        self.assertEqual(
            set(KNOWLEDGE_FILES),
            {
                "company_overview.md", "personas.md", "product_strategy.md",
                "architecture.md", "roadmap.md",
            },
        )
        self.assertTrue(all(path.parent == KNOWLEDGE_DIR.resolve() for path in knowledge_paths()))
        self.assertTrue(all(path.suffix == ".md" for path in knowledge_paths()))

    def test_sensitive_and_non_knowledge_sources_are_excluded(self) -> None:
        indexed_names = set(KNOWLEDGE_FILES)
        self.assertNotIn("ground_truth.md", indexed_names)
        self.assertFalse(any(name.endswith(".csv") for name in indexed_names))
        self.assertFalse(any("test" in name.lower() for name in indexed_names))

    def test_checked_in_indexing_configuration_is_valid(self) -> None:
        config = load_config(CONFIG_PATH)
        self.assertEqual(config["vector_store_name"], VECTOR_STORE_NAME)
        if config["vector_store_id"] is None:
            self.assertEqual(config["files"], {})
        else:
            self.assertTrue(is_valid_vector_store_id(config["vector_store_id"]))
            self.assertEqual(set(config["files"]), set(KNOWLEDGE_FILES))
            self.assertTrue(all(entry["status"] == "completed" for entry in config["files"].values()))

    def test_config_rejects_non_allowlisted_manifest_entries(self) -> None:
        config = default_config()
        config["files"] = {"not-allowlisted.md": {"file_id": "file_test"}}
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_missing_config_falls_back_to_safe_unconfigured_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config = load_config(Path(temporary_directory) / "missing.json")
        self.assertIsNone(config["vector_store_id"])
        self.assertEqual(config["files"], {})

    def test_production_code_never_references_developer_ground_truth(self) -> None:
        production_paths = [PROJECT_ROOT / "app.py"]
        for directory in ["agents", "rag", "scripts", "tools"]:
            production_paths.extend((PROJECT_ROOT / directory).glob("*.py"))
        forbidden_name = "ground" + "_truth"
        for path in production_paths:
            with self.subTest(path=path):
                self.assertNotIn(forbidden_name, path.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
