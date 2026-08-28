"""Validate the deterministic, fully synthetic Phase 2 dataset."""

from __future__ import annotations

import csv
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data"
UNWANTED = {"spam", "fraud", "robocall"}
EU_COUNTRIES = {"Germany", "France", "Ireland", "Netherlands", "Spain"}


def read_csv(filename: str) -> list[dict[str, str]]:
    with (DATA / filename).open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


class SyntheticDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.customers = read_csv("customers.csv")
        cls.calls = read_csv("calls.csv")
        cls.models = read_csv("model_versions.csv")
        cls.tickets = read_csv("support_tickets.csv")
        cls.usage = read_csv("product_usage.csv")
        cls.experiments = read_csv("experiments.csv")

    def test_required_columns_exist(self) -> None:
        required = {
            "customers.csv": {"customer_id", "customer_name", "customer_segment", "ARR", "carrier", "country"},
            "calls.csv": {"customer_id", "carrier", "country", "call_category", "predicted_category", "confidence", "actual_category", "latency_ms", "blocked", "model_version"},
            "model_versions.csv": {"model_version", "unwanted_call_precision", "unwanted_call_recall"},
            "support_tickets.csv": {"customer_id", "customer_segment", "complaint_type", "severity", "ticket_date", "model_version"},
            "product_usage.csv": {"customer_id", "monthly_api_volume", "uptime", "retention_risk"},
            "experiments.csv": {"experiment_id", "aggregate_lift", "tier_1_carrier_lift"},
        }
        datasets = {
            "customers.csv": self.customers, "calls.csv": self.calls,
            "model_versions.csv": self.models, "support_tickets.csv": self.tickets,
            "product_usage.csv": self.usage, "experiments.csv": self.experiments,
        }
        for filename, columns in required.items():
            with self.subTest(filename=filename):
                self.assertTrue(columns.issubset(datasets[filename][0]))

    def test_record_counts(self) -> None:
        self.assertEqual(len(self.customers), 100)
        self.assertGreaterEqual(len(self.calls), 24_000)
        self.assertLessEqual(len(self.calls), 26_000)
        self.assertEqual(len(self.models), 3)
        self.assertEqual(len(self.usage), 1_200)
        self.assertGreaterEqual(len(self.tickets), 900)
        self.assertLessEqual(len(self.tickets), 1_100)
        self.assertGreaterEqual(len(self.experiments), 10)
        self.assertLessEqual(len(self.experiments), 15)

    def test_cross_file_ids_are_consistent(self) -> None:
        customer_ids = {row["customer_id"] for row in self.customers}
        model_versions = {row["model_version"] for row in self.models}
        self.assertTrue({row["customer_id"] for row in self.calls}.issubset(customer_ids))
        self.assertTrue({row["customer_id"] for row in self.tickets}.issubset(customer_ids))
        self.assertTrue({row["customer_id"] for row in self.usage}.issubset(customer_ids))
        self.assertTrue({row["model_version"] for row in self.calls}.issubset(model_versions))
        self.assertTrue({row["model_version"] for row in self.tickets}.issubset(model_versions))
        self.assertTrue({row["model_version"] for row in self.usage}.issubset(model_versions))

    @staticmethod
    def precision_recall(rows: list[dict[str, str]], version: str) -> tuple[float, float]:
        selected = [row for row in rows if row["model_version"] == version]
        tp = sum(row["actual_category"] in UNWANTED and row["predicted_category"] in UNWANTED for row in selected)
        fp = sum(row["actual_category"] == "legitimate" and row["predicted_category"] in UNWANTED for row in selected)
        fn = sum(row["actual_category"] in UNWANTED and row["predicted_category"] == "legitimate" for row in selected)
        return tp / (tp + fp), tp / (tp + fn)

    def test_v32_precision_recall_tradeoff(self) -> None:
        precision_31, recall_31 = self.precision_recall(self.calls, "v3.1")
        precision_32, recall_32 = self.precision_recall(self.calls, "v3.2")
        self.assertGreater(recall_32, recall_31 + 0.07)
        self.assertLess(precision_32, precision_31 - 0.07)

    def test_v32_complaints_are_concentrated_in_tier_one_carriers(self) -> None:
        v32_false_positives = [
            row for row in self.tickets
            if row["model_version"] == "v3.2" and row["complaint_type"] == "false_positive"
        ]
        earlier_tier_one_false_positives = [
            row for row in self.tickets
            if row["model_version"] != "v3.2"
            and row["complaint_type"] == "false_positive"
            and row["customer_segment"] == "Tier 1 Carrier"
        ]
        tier_one_share = sum(row["customer_segment"] == "Tier 1 Carrier" for row in v32_false_positives) / len(v32_false_positives)
        v32_tier_one_per_month = sum(row["customer_segment"] == "Tier 1 Carrier" for row in v32_false_positives) / 4
        earlier_tier_one_per_month = len(earlier_tier_one_false_positives) / 8
        self.assertGreater(tier_one_share, 0.65)
        self.assertGreater(v32_tier_one_per_month, earlier_tier_one_per_month * 5)

    def test_eu_latency_increase_is_measurable(self) -> None:
        cutoff = date(2025, 7, 15)
        before = [float(row["latency_ms"]) for row in self.calls if row["country"] in EU_COUNTRIES and date.fromisoformat(row["call_date"]) < cutoff]
        after = [float(row["latency_ms"]) for row in self.calls if row["country"] in EU_COUNTRIES and date.fromisoformat(row["call_date"]) >= cutoff]
        self.assertGreater(sum(after) / len(after), sum(before) / len(before) + 50)

    def test_high_arr_customer_has_quality_driven_churn_risk(self) -> None:
        high_arr_ids = {row["customer_id"] for row in self.customers if float(row["ARR"]) >= 1_000_000}
        risky_rows = [row for row in self.usage if row["customer_id"] in high_arr_ids and row["retention_risk"] == "high" and float(row["uptime"]) < 0.995]
        self.assertTrue(risky_rows)

    def test_high_explainability_usage_has_low_action_rate(self) -> None:
        queries = sum(int(row["explainability_queries"]) for row in self.usage)
        actions = sum(int(row["explanations_actioned"]) for row in self.usage)
        self.assertGreater(queries, 100_000)
        self.assertLess(actions / queries, 0.03)

    def test_positive_experiment_harms_tier_one_segment(self) -> None:
        conflicts = [row for row in self.experiments if float(row["aggregate_lift"]) > 0.05 and float(row["tier_1_carrier_lift"]) < -0.05]
        self.assertTrue(conflicts)


if __name__ == "__main__":
    unittest.main()
