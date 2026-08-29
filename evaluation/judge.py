"""Optional model-based qualitative evaluation; never affects production answers."""

from __future__ import annotations

import json

from agents import Agent, Runner


JUDGE_INSTRUCTIONS = """
You evaluate a fictional AI Product Manager response. Score each dimension from 1
to 5: recommendation_quality, appropriate_uncertainty, avoids_unsupported_causality,
evidence_synthesis, and pm_judgment. Return JSON only with those five integer fields
and a short rationale. This is model-based evaluation, not objective ground truth.
Do not reveal hidden reasoning.
""".strip()


def judge_response(question: str, response: str, expected_characteristics: list[list[str]]) -> dict:
    judge = Agent(name="Evaluation Judge", instructions=JUDGE_INSTRUCTIONS)
    prompt = json.dumps({"question": question, "response": response,
                         "expected_characteristics": expected_characteristics})
    result = Runner.run_sync(judge, prompt)
    try:
        scores = json.loads(str(result.final_output))
    except json.JSONDecodeError:
        return {"available": False, "error": "Judge did not return valid JSON."}
    scores["available"] = True
    scores["label"] = "model-based evaluation"
    return scores
