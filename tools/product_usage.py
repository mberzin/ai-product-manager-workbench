"""Feature-adoption and experiment-analysis tools."""

from __future__ import annotations

from agents import function_tool

from tools.data_access import date_filter, error_result, load_data, time_period, to_json


VALID_FEATURES = {"explainability"}


@function_tool
def analyze_feature_usage(
    feature: str = "explainability",
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Analyze feature adoption and measurable action conversion over time.

    Use to distinguish high feature usage from demonstrated customer value. The
    current synthetic dataset supports the explainability feature.
    """
    if feature not in VALID_FEATURES:
        return error_result(f"Unknown feature '{feature}'.", allowed_features=sorted(VALID_FEATURES))
    usage = load_data("product_usage.csv")
    usage, error = date_filter(usage, "usage_month", start_date, end_date)
    if error:
        return error_result(error)
    if usage.empty:
        return error_result("No product-usage records match the requested dates.")
    monthly = usage.groupby(usage["usage_month"].dt.to_period("M")).agg(
        customer_count=("customer_id", "nunique"), queries=("explainability_queries", "sum"),
        actions=("explanations_actioned", "sum"),
    ).reset_index()
    monthly["usage_month"] = monthly["usage_month"].astype(str)
    monthly["action_rate"] = (monthly["actions"] / monthly["queries"]).round(4)
    total_queries = int(usage["explainability_queries"].sum())
    total_actions = int(usage["explanations_actioned"].sum())
    return to_json(
        {"status": "ok", "feature": feature,
         "metric_definitions": {"queries": "Explainability views/queries", "actions": "Queries followed by a recorded analyst action",
                                "action_rate": "actions / queries; adoption alone is not causal business value"},
         "sample_size": len(usage), "customer_count": int(usage["customer_id"].nunique()),
         "time_period": time_period(usage, "usage_month"),
         "summary": {"queries": total_queries, "actions": total_actions, "action_rate": round(total_actions / total_queries, 4)},
         "monthly_results": monthly.to_dict("records")}
    )


@function_tool
def analyze_experiment(experiment_id: str) -> str:
    """Return the outcome, sample size, significance flag, and segment lifts for one experiment.

    Use before deciding whether a named product experiment was successful. A positive
    aggregate result should still be checked for strategically important segments.
    """
    experiments = load_data("experiments.csv")
    selected = experiments[experiments["experiment_id"].str.upper() == experiment_id.upper()]
    if selected.empty:
        return error_result(f"Unknown experiment_id '{experiment_id}'.", allowed=experiments["experiment_id"].tolist())
    row = selected.iloc[0]
    return to_json(
        {"status": "ok", "definition": "Lift values are relative changes in the experiment's primary metric versus control",
         "result": {"experiment_id": row["experiment_id"], "experiment_name": row["experiment_name"],
                    "start_date": row["start_date"], "primary_metric": row["primary_metric"],
                    "sample_size": int(row["sample_size"]), "aggregate_lift": round(float(row["aggregate_lift"]), 4),
                    "statistically_significant": str(row["statistically_significant"]).lower() == "true",
                    "conclusion": row["conclusion"],
                    "tier_1_carrier_lift": round(float(row["tier_1_carrier_lift"]), 4),
                    "enterprise_bank_lift": round(float(row["enterprise_bank_lift"]), 4),
                    "mid_market_lift": round(float(row["mid_market_lift"]), 4)}}
    )


@function_tool
def compare_experiment_segments(experiment_id: str) -> str:
    """Compare one experiment's aggregate lift with its customer-segment lifts.

    Use to find heterogeneous treatment effects or cases where a positive aggregate
    hides harm to Tier 1 carriers, enterprise banks, or mid-market customers.
    """
    experiments = load_data("experiments.csv")
    selected = experiments[experiments["experiment_id"].str.upper() == experiment_id.upper()]
    if selected.empty:
        return error_result(f"Unknown experiment_id '{experiment_id}'.", allowed=experiments["experiment_id"].tolist())
    row = selected.iloc[0]
    aggregate = float(row["aggregate_lift"])
    segments = [
        {"segment": "Tier 1 Carrier", "lift": round(float(row["tier_1_carrier_lift"]), 4)},
        {"segment": "Enterprise Bank", "lift": round(float(row["enterprise_bank_lift"]), 4)},
        {"segment": "Mid-Market", "lift": round(float(row["mid_market_lift"]), 4)},
    ]
    for segment in segments:
        segment["difference_from_aggregate"] = round(segment["lift"] - aggregate, 4)
        segment["direction_conflicts_with_aggregate"] = (segment["lift"] < 0 < aggregate) or (segment["lift"] > 0 > aggregate)
    return to_json(
        {"status": "ok", "experiment_id": row["experiment_id"], "experiment_name": row["experiment_name"],
         "primary_metric": row["primary_metric"], "sample_size": int(row["sample_size"]),
         "definition": "Lift is relative to control; segment rows share the experiment sample and are directional synthetic summaries",
         "aggregate_lift": round(aggregate, 4), "segments": segments}
    )
