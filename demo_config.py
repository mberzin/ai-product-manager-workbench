"""Small, deployment-safe limits for the public portfolio demo.

The limits are intentionally independent from agent behavior. Operators may tune
them with environment variables without editing application code.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class DemoLimits:
    """Resource limits applied to one Streamlit browser session."""

    max_prompt_chars: int = 2_000
    max_history_messages: int = 12
    max_requests_per_session: int = 8


_BOUNDS = {
    "CALLGUARD_MAX_PROMPT_CHARS": (100, 10_000),
    "CALLGUARD_MAX_HISTORY_MESSAGES": (2, 40),
    "CALLGUARD_MAX_REQUESTS_PER_SESSION": (1, 50),
}


def _bounded_int(environment: Mapping[str, str], name: str, default: int) -> int:
    """Return a valid configured integer, otherwise retain the safe default."""
    raw_value = environment.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    minimum, maximum = _BOUNDS[name]
    return value if minimum <= value <= maximum else default


def load_demo_limits(environment: Mapping[str, str] | None = None) -> DemoLimits:
    """Load configurable limits from an environment-like mapping."""
    values = os.environ if environment is None else environment
    defaults = DemoLimits()
    return DemoLimits(
        max_prompt_chars=_bounded_int(
            values, "CALLGUARD_MAX_PROMPT_CHARS", defaults.max_prompt_chars
        ),
        max_history_messages=_bounded_int(
            values, "CALLGUARD_MAX_HISTORY_MESSAGES", defaults.max_history_messages
        ),
        max_requests_per_session=_bounded_int(
            values,
            "CALLGUARD_MAX_REQUESTS_PER_SESSION",
            defaults.max_requests_per_session,
        ),
    )


def validate_prompt(prompt: str, limits: DemoLimits) -> str | None:
    """Return a friendly validation error or ``None`` for an accepted prompt."""
    if not prompt.strip():
        return "Enter a product question before submitting."
    if len(prompt) > limits.max_prompt_chars:
        return f"Keep the question under {limits.max_prompt_chars:,} characters."
    return None


def request_limit_reached(request_count: int, limits: DemoLimits) -> bool:
    """Return whether this browser session has exhausted its request allowance."""
    return request_count >= limits.max_requests_per_session


def bounded_history(messages: Sequence[dict], maximum: int) -> list[dict]:
    """Keep only the newest messages sent to the model and retained in session."""
    return list(messages[-maximum:])
