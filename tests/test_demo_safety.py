"""Deterministic checks for Phase 7 demo and deployment safeguards."""

import ast
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

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

    def test_demo_questions_and_capability_labels_are_exact(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        module = ast.parse(app_source)
        assignment = next(
            node
            for node in module.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "DEMO_QUESTIONS"
                for target in node.targets
            )
        )
        questions = ast.literal_eval(assignment.value)
        self.assertEqual(
            questions,
            (
                (
                    "EU latency diagnosis",
                    "Quantitative analysis",
                    "What happened to EU latency?",
                    False,
                ),
                (
                    "Customer personas",
                    "Knowledge retrieval",
                    "Who are CallGuard's main personas and what matters most to them?",
                    False,
                ),
                (
                    "Featured · Tier 1 rollback",
                    "Full multi-agent decision",
                    "Should we roll back v3.2 specifically for Tier 1 carriers? Consider "
                    "model performance, customer strategy, and technical mitigation options.",
                    True,
                ),
                (
                    "Product prioritization",
                    "Data + strategy",
                    "Should CallGuard prioritize fixing v3.2 or investing further in "
                    "explainability?",
                    False,
                ),
            ),
        )

    def test_execution_transparency_remains_collapsed_and_complete(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        for label in (
            "Agents involved",
            "Tools used",
            "Knowledge used",
            "Execution metadata",
            "Response latency",
            "Model requests",
            "Input tokens",
            "Output tokens",
            "Total tokens",
        ):
            self.assertIn(label, app_source)
        self.assertGreaterEqual(app_source.count("expanded=False"), 5)

    def test_conversation_focus_is_fixed_and_one_shot(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('CONVERSATION_ANCHOR_ID = "conversation-result-anchor"', app_source)
        self.assertIn('data={"focusToken": focus_token}', app_source)
        self.assertIn("focusToken === previousToken", app_source)
        self.assertIn("target.dataset.lastFocusToken = String(focusToken)", app_source)

    def test_buttons_queue_exact_questions_and_request_focus(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("on_click=queue_product_problem", app_source)
        self.assertIn("args=(question,)", app_source)
        self.assertIn("next_token = current_token + 1", app_source)
        self.assertIn("st.session_state.request_focus_sequence = next_token", app_source)

    def test_focus_advances_only_after_user_request_boundary(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        user_boundary = app_source.rindex('with content.chat_message("user")')
        focus_call = app_source.rindex(
            "show_conversation_focus_target(focus_token=active_focus_token)"
        )
        assistant_boundary = app_source.rindex('with content.chat_message("assistant")')
        self.assertLess(user_boundary, focus_call)
        self.assertLess(focus_call, assistant_boundary)

    def test_ordinary_rerun_mounts_anchor_without_scrolling(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("if not focus_target_rendered:", app_source)
        self.assertIn(
            "show_conversation_focus_target(focus_token=0)", app_source
        )

    def test_custom_submission_uses_same_focus_lifecycle(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("queue_product_problem(question)", app_source)
        self.assertIn("on_submit=queue_custom_product_problem", app_source)

    def test_repeated_requests_generate_distinct_focus_tokens(self) -> None:
        # Empty key avoids API calls while exercising real Streamlit callbacks,
        # session state, chat ordering, and repeated canned submissions.
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            app = AppTest.from_file(ROOT / "app.py").run(timeout=30)

            next(
                button for button in app.button if button.key == "demo_question_0"
            ).click().run(timeout=30)
            first_token = app.session_state["request_focus_sequence"]
            self.assertEqual(app.session_state["messages"][0]["content"],
                             "What happened to EU latency?")

            # An ordinary rerun, including one caused by non-request UI activity,
            # must not manufacture a new scroll token.
            app.run(timeout=30)
            self.assertEqual(app.session_state["request_focus_sequence"], first_token)

            next(
                button for button in app.button if button.key == "demo_question_1"
            ).click().run(timeout=30)
            second_token = app.session_state["request_focus_sequence"]
            self.assertEqual(second_token, first_token + 1)
            self.assertEqual(
                app.session_state["messages"][-2]["content"],
                "Who are CallGuard's main personas and what matters most to them?",
            )

            next(
                button for button in app.button if button.key == "demo_question_2"
            ).click().run(timeout=30)
            third_token = app.session_state["request_focus_sequence"]
            self.assertEqual(third_token, second_token + 1)
            self.assertEqual(
                app.session_state["messages"][-2]["content"],
                "Should we roll back v3.2 specifically for Tier 1 carriers? Consider "
                "model performance, customer strategy, and technical mitigation options.",
            )

            app.chat_input[0].set_value("A custom product question").run(timeout=30)
            self.assertEqual(
                app.session_state["request_focus_sequence"], third_token + 1
            )
            self.assertEqual(len(app.chat_input), 1)

    def test_single_custom_input_is_after_response_processing(self) -> None:
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertEqual(app_source.count("st.chat_input("), 1)
        chat_input_position = app_source.rindex("st.chat_input(")
        response_history_position = app_source.rindex('"role": "assistant"')
        self.assertGreater(chat_input_position, response_history_position)
        self.assertIn("on_submit=queue_custom_product_problem", app_source)

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
