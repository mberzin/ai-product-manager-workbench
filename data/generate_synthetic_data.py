"""Generate the deterministic Phase 2 dataset for fictional CallGuard AI.

All names and records produced by this script are synthetic. The rules below are
deliberately explicit so learners can understand how the six evaluation scenarios
are encoded and can regenerate the CSV files with the same random seed.
"""

from __future__ import annotations

import csv
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path


SEED = 20250828
RNG = random.Random(SEED)
DATA_DIR = Path(__file__).resolve().parent
START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 12, 31)
V32_DATE = date(2025, 9, 1)
EU_INFRA_CHANGE_DATE = date(2025, 7, 15)

EU_COUNTRIES = ["Germany", "France", "Ireland", "Netherlands", "Spain"]
NON_EU_COUNTRIES = ["United States", "Canada", "Australia"]
ACTUAL_CATEGORIES = ["legitimate", "spam", "fraud", "robocall"]
UNWANTED_CATEGORIES = {"spam", "fraud", "robocall"}


def write_csv(filename: str, rows: list[dict]) -> None:
    """Write rows with stable column ordering taken from the first row."""
    path = DATA_DIR / filename
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def random_date(start: date, end: date) -> date:
    """Return a uniformly distributed date in an inclusive range."""
    return start + timedelta(days=RNG.randint(0, (end - start).days))


def model_for_date(event_date: date) -> str:
    if event_date >= V32_DATE:
        return "v3.2"
    if event_date >= date(2025, 5, 1):
        return "v3.1"
    return "v3.0"


def build_customers() -> list[dict]:
    """Create 100 fictional customers across four target customer types."""
    prefixes = [
        "Northstar", "Alder", "Bluepeak", "Cinder", "Driftwood", "Everfield",
        "Fairway", "Granite", "Harbor", "Ironwood", "Juniper", "Keystone",
        "Lighthouse", "Meadow", "Nimbus", "Oakline", "Pioneer", "Quartz",
        "Redwood", "Summit", "Tandem", "Union", "Vantage", "Willow", "Zenith",
    ]
    suffixes = ["Mobile", "Bank", "Connect", "CX", "Telecom", "Financial", "Cloud", "Voice"]
    customers: list[dict] = []

    for number in range(1, 101):
        if number <= 20:
            customer_type = "mobile_carrier"
            segment = "Tier 1 Carrier" if number <= 8 else "Regional Carrier"
            arr_range = (1_200_000, 3_200_000) if number <= 8 else (250_000, 900_000)
        elif number <= 45:
            customer_type = "bank"
            segment = "Enterprise Bank" if number <= 32 else "Mid-Market Bank"
            arr_range = (700_000, 2_200_000) if number <= 32 else (180_000, 650_000)
        elif number <= 75:
            customer_type = "contact_center"
            segment = "Enterprise Contact Center" if number <= 58 else "Mid-Market Contact Center"
            arr_range = (450_000, 1_400_000) if number <= 58 else (120_000, 450_000)
        else:
            customer_type = "communications_platform"
            segment = "Enterprise CPaaS" if number <= 88 else "Growth CPaaS"
            arr_range = (600_000, 1_800_000) if number <= 88 else (150_000, 550_000)

        country_pool = EU_COUNTRIES if number % 3 == 0 else NON_EU_COUNTRIES
        country = RNG.choice(country_pool)
        name = f"{prefixes[(number - 1) % len(prefixes)]} {suffixes[(number * 3) % len(suffixes)]}"
        arr = RNG.randrange(arr_range[0] // 10_000, arr_range[1] // 10_000 + 1) * 10_000

        # CUST-001 is the intentionally important, quality-sensitive account.
        if number == 1:
            name, country, arr = "Northstar Mobile", "United States", 2_800_000

        customers.append(
            {
                "customer_id": f"CUST-{number:03d}",
                "customer_name": name,
                "customer_type": customer_type,
                "customer_segment": segment,
                "ARR": arr,
                "country": country,
                "carrier": name if customer_type == "mobile_carrier" else RNG.choice(
                    ["Northstar Mobile", "Alder Telecom", "Bluepeak Mobile", "multi-carrier"]
                ),
                "contract_start_date": random_date(date(2022, 1, 1), date(2024, 12, 31)).isoformat(),
                "account_status": "at_risk" if number in {1, 3, 27} else "active",
            }
        )
    return customers


def choose_prediction(actual: str, version: str) -> tuple[str, float]:
    """Encode v3.2's higher unwanted-call recall and lower precision."""
    recall = {"v3.0": 0.76, "v3.1": 0.83, "v3.2": 0.94}[version]
    false_positive_rate = {"v3.0": 0.025, "v3.1": 0.020, "v3.2": 0.105}[version]

    if actual in UNWANTED_CATEGORIES:
        if RNG.random() < recall:
            predicted = actual if RNG.random() < 0.82 else RNG.choice(sorted(UNWANTED_CATEGORIES))
            confidence = RNG.uniform(0.76, 0.99)
        else:
            predicted = "legitimate"
            confidence = RNG.uniform(0.52, 0.76)
    elif RNG.random() < false_positive_rate:
        predicted = RNG.choice(sorted(UNWANTED_CATEGORIES))
        confidence = RNG.uniform(0.55, 0.87)
    else:
        predicted = "legitimate"
        confidence = RNG.uniform(0.80, 0.995)
    return predicted, round(confidence, 3)


def build_calls(customers: list[dict], count: int = 25_000) -> list[dict]:
    """Generate call classifications with model and regional effects."""
    customer_weights = [float(customer["ARR"]) ** 0.55 for customer in customers]
    calls: list[dict] = []

    for number in range(1, count + 1):
        customer = RNG.choices(customers, weights=customer_weights, k=1)[0]
        call_date = random_date(START_DATE, END_DATE)
        version = model_for_date(call_date)
        actual = RNG.choices(ACTUAL_CATEGORIES, weights=[0.62, 0.19, 0.08, 0.11], k=1)[0]
        predicted, confidence = choose_prediction(actual, version)

        country = customer["country"]
        base_latency = {
            "United States": 82, "Canada": 91, "Australia": 118,
            "Germany": 105, "France": 108, "Ireland": 101,
            "Netherlands": 103, "Spain": 112,
        }[country]
        # Scenario C: an EU routing change adds a visible ~70 ms after July 15.
        if country in EU_COUNTRIES and call_date >= EU_INFRA_CHANGE_DATE:
            base_latency += 70
        latency = max(35, round(RNG.gauss(base_latency, 16)))
        blocked = predicted in UNWANTED_CATEGORIES and confidence >= 0.68

        calls.append(
            {
                "call_id": f"CALL-{number:06d}",
                "customer_id": customer["customer_id"],
                "call_date": call_date.isoformat(),
                "carrier": customer["carrier"],
                "country": country,
                "call_category": actual,
                "predicted_category": predicted,
                "confidence": confidence,
                "actual_category": actual,
                "latency_ms": latency,
                "blocked": str(blocked).lower(),
                "model_version": version,
            }
        )
    return calls


def calculate_model_metrics(calls: list[dict], version: str) -> tuple[float, float]:
    """Calculate binary unwanted-call precision and recall from call-level data."""
    version_calls = [row for row in calls if row["model_version"] == version]
    true_positive = sum(
        row["actual_category"] in UNWANTED_CATEGORIES
        and row["predicted_category"] in UNWANTED_CATEGORIES
        for row in version_calls
    )
    false_positive = sum(
        row["actual_category"] == "legitimate"
        and row["predicted_category"] in UNWANTED_CATEGORIES
        for row in version_calls
    )
    false_negative = sum(
        row["actual_category"] in UNWANTED_CATEGORIES
        and row["predicted_category"] == "legitimate"
        for row in version_calls
    )
    precision = true_positive / (true_positive + false_positive)
    recall = true_positive / (true_positive + false_negative)
    return round(precision, 4), round(recall, 4)


def build_model_versions(calls: list[dict]) -> list[dict]:
    notes = {
        "v3.0": "Baseline ensemble for spam, fraud, and robocall classification.",
        "v3.1": "Calibration and carrier reputation improvements.",
        "v3.2": "Recall-focused graph features; monitored for legitimate-call false positives.",
    }
    releases = {"v3.0": "2025-01-01", "v3.1": "2025-05-01", "v3.2": "2025-09-01"}
    rows = []
    for version in ["v3.0", "v3.1", "v3.2"]:
        precision, recall = calculate_model_metrics(calls, version)
        rows.append(
            {
                "model_version": version,
                "release_date": releases[version],
                "unwanted_call_precision": precision,
                "unwanted_call_recall": recall,
                "status": "active" if version == "v3.2" else "retired",
                "release_notes": notes[version],
            }
        )
    return rows


def build_support_tickets(customers: list[dict], count: int = 1_000) -> list[dict]:
    """Generate tickets aligned to v3.2 quality issues and affected accounts."""
    rows: list[dict] = []
    customer_by_id = {customer["customer_id"]: customer for customer in customers}
    tier_one = [customer for customer in customers if customer["customer_segment"] == "Tier 1 Carrier"]
    everyone_else = [customer for customer in customers if customer not in tier_one]

    for number in range(1, count + 1):
        is_v32_period = number <= 470
        if is_v32_period:
            ticket_date = random_date(V32_DATE, END_DATE)
            # Scenario B: most post-v3.2 false-positive complaints hit Tier 1 carriers,
            # with Northstar Mobile receiving the largest account-level concentration.
            if RNG.random() < 0.63:
                customer = RNG.choices(tier_one, weights=[8] + [1] * 7, k=1)[0]
                complaint = RNG.choices(
                    ["false_positive", "missed_spam", "latency", "availability", "billing", "integration"],
                    weights=[68, 7, 8, 6, 3, 8], k=1,
                )[0]
            else:
                customer = RNG.choice(everyone_else)
                complaint = RNG.choices(
                    ["false_positive", "missed_spam", "latency", "availability", "billing", "integration"],
                    weights=[24, 18, 17, 13, 10, 18], k=1,
                )[0]
        else:
            ticket_date = random_date(START_DATE, date(2025, 8, 31))
            customer = RNG.choice(customers)
            complaint = RNG.choices(
                ["false_positive", "missed_spam", "latency", "availability", "billing", "integration"],
                weights=[12, 25, 16, 13, 12, 22], k=1,
            )[0]

        severity_weights = [14, 36, 42, 8] if complaint in {"false_positive", "availability"} else [7, 29, 50, 14]
        severity = RNG.choices(["critical", "high", "medium", "low"], weights=severity_weights, k=1)[0]
        rows.append(
            {
                "ticket_id": f"TKT-{number:05d}",
                "customer_id": customer["customer_id"],
                "customer_segment": customer["customer_segment"],
                "complaint_type": complaint,
                "severity": severity,
                "ticket_date": ticket_date.isoformat(),
                "model_version": model_for_date(ticket_date),
                "status": RNG.choices(["resolved", "closed", "open"], weights=[58, 32, 10], k=1)[0],
                "resolution_hours": round(RNG.uniform(2, 120), 1),
            }
        )
    RNG.shuffle(rows)
    # Restore stable IDs after shuffle so reruns remain readable and unique.
    for index, row in enumerate(rows, 1):
        row["ticket_id"] = f"TKT-{index:05d}"
        assert row["customer_id"] in customer_by_id
    return rows


def month_start(month: int) -> date:
    return date(2025, month, 1)


def build_product_usage(customers: list[dict]) -> list[dict]:
    """Create one usage row per customer per month (100 x 12 = 1,200)."""
    rows: list[dict] = []
    segment_volume = {
        "Tier 1 Carrier": 18_000_000, "Regional Carrier": 5_500_000,
        "Enterprise Bank": 7_000_000, "Mid-Market Bank": 2_000_000,
        "Enterprise Contact Center": 4_200_000, "Mid-Market Contact Center": 1_300_000,
        "Enterprise CPaaS": 8_500_000, "Growth CPaaS": 2_600_000,
    }

    for customer in customers:
        for month in range(1, 13):
            period = month_start(month)
            baseline = segment_volume[customer["customer_segment"]]
            volume = round(baseline * (1 + 0.018 * (month - 1)) * RNG.uniform(0.82, 1.18))
            uptime = RNG.uniform(0.9985, 0.99995)
            retention_risk = "low"

            # Scenario D: Northstar's post-v3.2 reliability and quality degrade.
            if customer["customer_id"] == "CUST-001" and month >= 9:
                uptime = RNG.uniform(0.982, 0.991)
                retention_risk = "high"
            elif customer["customer_id"] in {"CUST-003", "CUST-027"} and month >= 8:
                uptime = RNG.uniform(0.991, 0.996)
                retention_risk = "medium"

            # Scenario E: explainability is opened frequently but rarely changes a
            # decision or creates a saved workflow/business-value event.
            explainability_queries = round(volume / RNG.uniform(2600, 3900))
            explanations_actioned = round(explainability_queries * RNG.uniform(0.006, 0.022))
            rows.append(
                {
                    "customer_id": customer["customer_id"],
                    "usage_month": period.isoformat(),
                    "model_version": model_for_date(period),
                    "monthly_api_volume": volume,
                    "uptime": round(uptime, 5),
                    "explainability_queries": explainability_queries,
                    "explanations_actioned": explanations_actioned,
                    "rules_configured": RNG.randint(1, 24),
                    "retention_risk": retention_risk,
                }
            )
    return rows


def build_experiments() -> list[dict]:
    """Create 12 fictional product experiments, including a segment reversal."""
    names = [
        "Confidence threshold presets", "Carrier reputation cache", "Fraud reason codes",
        "Bulk number review", "Adaptive retry policy", "Analyst digest email",
        "Low-latency endpoint", "Auto-block recommendations", "Webhook replay",
        "Custom category mapping", "Usage anomaly alerts", "Onboarding checklist",
    ]
    rows = []
    for index, name in enumerate(names, 1):
        aggregate_lift = round(RNG.uniform(-0.025, 0.085), 4)
        tier_one_lift = round(aggregate_lift + RNG.uniform(-0.025, 0.025), 4)
        conclusion = "neutral" if abs(aggregate_lift) < 0.01 else ("positive" if aggregate_lift > 0 else "negative")

        # Scenario F: positive overall, harmful for strategically important carriers.
        if index == 8:
            aggregate_lift, tier_one_lift, conclusion = 0.067, -0.091, "segment_conflict"

        rows.append(
            {
                "experiment_id": f"EXP-{index:03d}",
                "experiment_name": name,
                "start_date": date(2025, index, 1).isoformat(),
                "primary_metric": "workflow_completion_rate" if index != 8 else "blocked_call_acceptance_rate",
                "sample_size": RNG.randint(1800, 16000),
                "aggregate_lift": aggregate_lift,
                "tier_1_carrier_lift": tier_one_lift,
                "enterprise_bank_lift": round(aggregate_lift + RNG.uniform(-0.02, 0.03), 4),
                "mid_market_lift": round(aggregate_lift + RNG.uniform(0.0, 0.04), 4),
                "statistically_significant": str(abs(aggregate_lift) >= 0.025).lower(),
                "conclusion": conclusion,
            }
        )
    return rows


def main() -> None:
    """Generate every Phase 2 CSV in dependency order."""
    customers = build_customers()
    calls = build_calls(customers)
    model_versions = build_model_versions(calls)
    support_tickets = build_support_tickets(customers)
    product_usage = build_product_usage(customers)
    experiments = build_experiments()

    write_csv("customers.csv", customers)
    write_csv("calls.csv", calls)
    write_csv("model_versions.csv", model_versions)
    write_csv("support_tickets.csv", support_tickets)
    write_csv("product_usage.csv", product_usage)
    write_csv("experiments.csv", experiments)

    print("Generated deterministic synthetic CallGuard AI data:")
    for filename, rows in [
        ("customers.csv", customers), ("calls.csv", calls),
        ("model_versions.csv", model_versions), ("support_tickets.csv", support_tickets),
        ("product_usage.csv", product_usage), ("experiments.csv", experiments),
    ]:
        print(f"  {filename}: {len(rows):,} rows")

    print("Call distribution by model:", dict(Counter(row["model_version"] for row in calls)))


if __name__ == "__main__":
    main()
