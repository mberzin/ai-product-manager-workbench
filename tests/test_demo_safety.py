"""Deterministic checks for Phase 7 demo and deployment safeguards."""

import subprocess
import unittest
from pathlib import Path

from demo_config import (
    DemoLimits,
    bounded_history,
    load_demo_limits,
    request_limit_reached,
    validate_prompt,
)


ROOT = Path(__file__).resolve().parents[1]


class DemoLimitTests(unittest.TestCase):
    def test_default_limits_are_bounded(self) -> None:
        limits = load_demo_limits({})
        self.assertEqual(limits, DemoLimits())
        self.assertLessEqual(limits.max_prompt_chars, 10_000)
        self.assertLessEqual(limits.max_requests_per_session, 50)

    def test_valid_environment_overrides_are_supported(self) -> None:
        limits = load_demo_limits(
            {
                "CALLGUARD_MAX_PROMPT_CHARS": "1500",
                "CALLGUARD_MAX_HISTORY_MESSAGES": "8",
                "CALLGUARD_MAX_REQUESTS_PER_SESSION": "5",
            }
        )
        self.assertEqual(limits, DemoLimits(1500, 8, 5))

    def test_invalid_or_unsafe_overrides_use_defaults(self) -> None:
        limits = load_demo_limits(
            {
                "CALLGUARD_MAX_PROMPT_CHARS": "unlimited",
                "CALLGUARD_MAX_HISTORY_MESSAGES": "5000",
                "CALLGUARD_MAX_REQUESTS_PER_SESSION": "0",
            }
        )
        self.assertEqual(limits, DemoLimits())

    def test_prompt_length_is_enforced(self) -> None:
        limits = DemoLimits(max_prompt_chars=100)
        self.assertIsNone(validate_prompt("What changed?", limits))
        self.assertIsNotNone(validate_prompt("x" * 101, limits))
        self.assertIsNotNone(validate_prompt("   ", limits))

    def test_history_keeps_only_newest_messages(self) -> None:
        messages = [{"content": str(index)} for index in range(6)]
        self.assertEqual(
            [message["content"] for message in bounded_history(messages, 3)],
            ["3", "4", "5"],
        )

    def test_session_request_limit_is_enforced_at_boundary(self) -> None:
        limits = DemoLimits(max_requests_per_session=3)
        self.assertFalse(request_limit_reached(2, limits))
        self.assertTrue(request_limit_reached(3, limits))
        self.assertTrue(request_limit_reached(4, limits))


class DeploymentSafetyTests(unittest.TestCase):
    def test_runtime_and_entry_point_are_portable(self) -> None:
        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.13")
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("C:\\\\", app_source)
        self.assertNotIn("accept_file", app_source)

    def test_synthetic_label_and_demo_questions_are_visible(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("all company, customer, and product data are synthetic", app_source)
        self.assertEqual(app_source.count("Featured · Tier 1 rollback"), 1)

    def test_env_is_ignored_and_example_is_placeholder_only(self) -> None:
        ignored = subprocess.run(
            ["git", "check-ignore", ".env"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ignored.returncode, 0)
        self.assertEqual((ROOT / ".env.example").read_text().strip(), "OPENAI_API_KEY=")

    def test_streamlit_secret_file_is_ignored(self) -> None:
        ignored = subprocess.run(
            ["git", "check-ignore", ".streamlit/secrets.toml"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ignored.returncode, 0)


if __name__ == "__main__":
    unittest.main()
