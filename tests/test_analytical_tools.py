"""Deterministic tests for each Phase 3 analytical tool family."""

from __future__ import annotations

import json
import unittest

from tools.customer_support import analyze_complaint_trends, identify_high_risk_customers, segment_complaints
from tools.model_performance import (
    calculate_false_positive_rate,
    calculate_precision,
    calculate_recall,
    compare_model_versions,
    segment_model_performance,
)
from tools.product_usage import analyze_experiment, analyze_feature_usage, compare_experiment_segments
from tools.reliability import analyze_latency_by_region, analyze_uptime_by_customer


def invoke(tool, *args, **kwargs) -> dict:
    """Call the original deterministic function beneath the SDK tool wrapper."""
    return json.loads(tool.__wrapped__(*args, **kwargs))


class ModelPerformanceToolTests(unittest.TestCase):
    def test_compare_model_versions_exposes_tradeoff(self) -> None:
        result = invoke(compare_model_versions)
        versions = {row["model_version"]: row for row in result["results"]}
        self.assertGreater(versions["v3.2"]["recall"], versions["v3.1"]["recall"])
        self.assertLess(versions["v3.2"]["precision"], versions["v3.1"]["precision"])
        self.assertGreater(versions["v3.2"]["false_positive_rate"], versions["v3.1"]["false_positive_rate"])
        self.assertIn("sample_size", versions["v3.2"])
        self.assertIn("time_period", versions["v3.2"])

    def test_individual_metrics_are_auditable(self) -> None:
        precision = invoke(calculate_precision, "v3.2")
        recall = invoke(calculate_recall, "v3.2")
        false_positive_rate = invoke(calculate_false_positive_rate, "v3.2")
        self.assertEqual(precision["status"], "ok")
        self.assertIn("confusion_counts", precision)
        self.assertAlmostEqual(recall["value"], 0.94, places=2)
        self.assertGreater(false_positive_rate["value"], 0.08)

    def test_segment_performance_is_bounded_and_invalid_inputs_are_safe(self) -> None:
        result = invoke(segment_model_performance, "v3.2", "customer_segment", 3)
        self.assertEqual(len(result["results"]), 3)
        invalid = invoke(segment_model_performance, "v3.2", "secret_column", 10)
        self.assertEqual(invalid["status"], "error")


class CustomerSupportToolTests(unittest.TestCase):
    def test_unfiltered_v32_counts_are_labeled_as_support_tickets(self) -> None:
        by_segment = invoke(segment_complaints, "customer_segment", "v3.2", None, 10)
        by_customer = invoke(segment_complaints, "customer_id", "v3.2", None, 10)

        self.assertEqual(by_segment["metric"], "support_ticket_count_and_share")
        self.assertIsNone(by_segment["filters"]["complaint_type"])
        self.assertEqual(by_segment["sample_size"], 470)
        self.assertEqual(by_segment["results"][0]["customer_segment"], "Tier 1 Carrier")
        self.assertEqual(by_segment["results"][0]["ticket_count"], 308)
        self.assertEqual(by_customer["results"][0]["customer_id"], "CUST-001")
        self.assertEqual(by_customer["results"][0]["ticket_count"], 151)
        self.assertIn("support-ticket counts", by_segment["terminology"])
        self.assertIn("complaint_type is non-null", by_segment["terminology"])

    def test_filtered_complaints_remain_distinct_from_all_support_tickets(self) -> None:
        filtered = invoke(
            segment_complaints,
            "customer_segment",
            "v3.2",
            "false_positive",
            10,
        )
        risk = invoke(identify_high_risk_customers, 1_000_000, 5)
        northstar = risk["results"][0]

        self.assertEqual(filtered["filters"]["complaint_type"], "false_positive")
        self.assertEqual(filtered["sample_size"], 246)
        self.assertEqual(filtered["results"][0]["ticket_count"], 208)
        self.assertEqual(northstar["v32_ticket_count"], 151)
        self.assertEqual(northstar["v32_false_positive_complaints"], 100)
        self.assertNotEqual(
            northstar["v32_ticket_count"],
            northstar["v32_false_positive_complaints"],
        )

    def test_complaint_trends_show_post_release_spike(self) -> None:
        result = invoke(analyze_complaint_trends, "false_positive")
        by_model = {}
        for row in result["results"]:
            by_model[row["model_version"]] = by_model.get(row["model_version"], 0) + row["ticket_count"]
        self.assertGreater(by_model["v3.2"], by_model["v3.1"])
        self.assertIn("time_period", result)

    def test_segment_complaints_finds_tier_one_concentration(self) -> None:
        result = invoke(segment_complaints, "customer_segment", "v3.2", "false_positive", 10)
        self.assertEqual(result["results"][0]["customer_segment"], "Tier 1 Carrier")
        self.assertGreater(result["results"][0]["share_of_filtered_tickets"], 0.8)

    def test_high_risk_customers_prioritize_northstar(self) -> None:
        result = invoke(identify_high_risk_customers, 1_000_000, 5)
        self.assertEqual(result["results"][0]["customer_id"], "CUST-001")
        self.assertEqual(result["results"][0]["latest_retention_risk"], "high")
        self.assertGreaterEqual(result["results"][0]["ARR"], 1_000_000)


class ReliabilityToolTests(unittest.TestCase):
    def test_latency_tool_measures_eu_before_after_change(self) -> None:
        result = invoke(analyze_latency_by_region, None, None, "2025-07-15")
        eu = {row["period"]: row for row in result["results"] if row["region"] == "EU"}
        self.assertGreater(eu["on_or_after"]["mean_latency_ms"], eu["before"]["mean_latency_ms"] + 50)
        self.assertGreater(eu["before"]["sample_size"], 0)

    def test_uptime_tool_returns_customer_evidence(self) -> None:
        result = invoke(analyze_uptime_by_customer, "CUST-001")
        customer = result["results"][0]
        self.assertEqual(customer["customer_id"], "CUST-001")
        self.assertLess(customer["minimum_uptime"], 0.99)
        self.assertEqual(customer["months_observed"], 12)


class ProductUsageAndExperimentToolTests(unittest.TestCase):
    def test_feature_usage_distinguishes_queries_from_actions(self) -> None:
        result = invoke(analyze_feature_usage, "explainability")
        self.assertGreater(result["summary"]["queries"], 100_000)
        self.assertLess(result["summary"]["action_rate"], 0.03)
        self.assertEqual(result["customer_count"], 100)

    def test_analyze_experiment_returns_exp008_evidence(self) -> None:
        result = invoke(analyze_experiment, "EXP-008")
        self.assertGreater(result["result"]["aggregate_lift"], 0)
        self.assertLess(result["result"]["tier_1_carrier_lift"], 0)
        self.assertGreater(result["result"]["sample_size"], 0)

    def test_compare_experiment_segments_flags_direction_conflict(self) -> None:
        result = invoke(compare_experiment_segments, "exp-008")
        tier_one = next(row for row in result["segments"] if row["segment"] == "Tier 1 Carrier")
        self.assertTrue(tier_one["direction_conflicts_with_aggregate"])

    def test_invalid_feature_and_experiment_are_safe(self) -> None:
        self.assertEqual(invoke(analyze_feature_usage, "unknown")["status"], "error")
        self.assertEqual(invoke(analyze_experiment, "EXP-999")["status"], "error")


if __name__ == "__main__":
    unittest.main()
