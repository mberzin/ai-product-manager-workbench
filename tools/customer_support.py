"""Customer health and support tools for synthetic CallGuard AI data."""

from __future__ import annotations

import pandas as pd
from agents import function_tool

from tools.data_access import bounded_limit, date_filter, error_result, load_data, time_period, to_json


VALID_COMPLAINT_DIMENSIONS = {"customer_segment", "customer_id", "severity", "model_version"}


@function_tool
def analyze_complaint_trends(
    complaint_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Summarize monthly support-ticket trends by ticket category and model version.

    Use for questions about support or complaint spikes, timing, or whether a release
    coincides with a change in ticket volume. Unfiltered counts represent all support
    tickets. A complaint_type filter returns that explicitly named ticket category.
    Counts are shown by month without raw tickets.
    """
    tickets = load_data("support_tickets.csv")
    if complaint_type and complaint_type not in set(tickets["complaint_type"]):
        return error_result(f"Unknown complaint_type '{complaint_type}'.", allowed=sorted(tickets["complaint_type"].unique()))
    tickets, error = date_filter(tickets, "ticket_date", start_date, end_date)
    if error:
        return error_result(error)
    if complaint_type:
        tickets = tickets[tickets["complaint_type"] == complaint_type]
    if tickets.empty:
        return error_result("No support tickets match the requested filters.")
    tickets["month"] = tickets["ticket_date"].dt.to_period("M").astype(str)
    grouped = (
        tickets.groupby(["month", "model_version", "complaint_type"])
        .size().rename("ticket_count").reset_index().sort_values(["month", "ticket_count"], ascending=[True, False])
    )
    return to_json(
        {"status": "ok", "metric": "support_ticket_count",
         "definition": "Number of synthetic support tickets created in each calendar month",
         "terminology": (
             "Counts are support tickets. When complaint_type is null, do not describe "
             "their total as complaints; when filtered, name the specific complaint_type."
         ),
         "sample_size": len(tickets), "time_period": time_period(tickets, "ticket_date"),
         "filters": {"complaint_type": complaint_type, "start_date": start_date, "end_date": end_date},
         "results": grouped.to_dict("records")}
    )


@function_tool
def segment_complaints(
    dimension: str = "customer_segment",
    model_version: str | None = None,
    complaint_type: str | None = None,
    limit: int = 10,
) -> str:
    """Rank support-ticket counts across segments, accounts, severity, or model.

    Use to determine where support volume or a specifically filtered complaint_type
    is concentrated. Without complaint_type, every result is an all-category support-
    ticket count, not a complaint count. Returns at most 20 groups.
    """
    if dimension not in VALID_COMPLAINT_DIMENSIONS:
        return error_result(f"Invalid dimension '{dimension}'.", allowed_dimensions=sorted(VALID_COMPLAINT_DIMENSIONS))
    tickets = load_data("support_tickets.csv")
    if model_version:
        if model_version not in set(tickets["model_version"]):
            return error_result(f"Unknown model_version '{model_version}'.")
        tickets = tickets[tickets["model_version"] == model_version]
    if complaint_type:
        if complaint_type not in set(tickets["complaint_type"]):
            return error_result(f"Unknown complaint_type '{complaint_type}'.")
        tickets = tickets[tickets["complaint_type"] == complaint_type]
    if tickets.empty:
        return error_result("No support tickets match the requested filters.")
    grouped = tickets.groupby(dimension).size().rename("ticket_count").reset_index()
    grouped["share_of_filtered_tickets"] = (grouped["ticket_count"] / len(tickets)).round(4)
    grouped = grouped.sort_values("ticket_count", ascending=False).head(bounded_limit(limit))
    return to_json(
        {"status": "ok", "metric": "support_ticket_count_and_share",
         "definition": "Ticket count and share within the requested model/complaint filters",
         "terminology": (
             "ticket_count and sample_size are support-ticket counts. Describe them as "
             "complaints only when complaint_type is non-null, and name that category."
         ),
         "sample_size": len(tickets), "time_period": time_period(tickets, "ticket_date"),
         "filters": {"model_version": model_version, "complaint_type": complaint_type, "dimension": dimension},
         "results": grouped.to_dict("records")}
    )


@function_tool
def identify_high_risk_customers(min_arr: float = 500000, limit: int = 10) -> str:
    """Identify high-ARR customers with retention, uptime, and complaint risk signals.

    Use for renewal prioritization or high-value customer risk questions. Risk is
    evidence-based: latest retention flag, recent uptime, and v3.2 complaint counts.
    This tool does not predict churn probability or assert root cause.
    """
    if min_arr < 0:
        return error_result("min_arr must be zero or greater.")
    customers = load_data("customers.csv")
    usage = load_data("product_usage.csv")
    tickets = load_data("support_tickets.csv")
    usage["usage_month"] = pd.to_datetime(usage["usage_month"])
    latest_month = usage["usage_month"].max()
    recent_start = latest_month - pd.DateOffset(months=3)
    recent = usage[usage["usage_month"] >= recent_start]
    usage_summary = recent.groupby("customer_id").agg(
        average_uptime=("uptime", "mean"),
        minimum_uptime=("uptime", "min"),
        latest_retention_risk=("retention_risk", "last"),
        monthly_api_volume=("monthly_api_volume", "mean"),
    ).reset_index()
    v32_tickets = tickets[tickets["model_version"] == "v3.2"]
    ticket_summary = v32_tickets.groupby("customer_id").agg(
        v32_ticket_count=("ticket_id", "count"),
        v32_false_positive_complaints=("complaint_type", lambda values: int((values == "false_positive").sum())),
    ).reset_index()
    result = customers.merge(usage_summary, on="customer_id", how="left").merge(ticket_summary, on="customer_id", how="left")
    result[["v32_ticket_count", "v32_false_positive_complaints"]] = result[["v32_ticket_count", "v32_false_positive_complaints"]].fillna(0).astype(int)
    risk_order = {"high": 3, "medium": 2, "low": 1}
    result["risk_rank"] = result["latest_retention_risk"].map(risk_order).fillna(0)
    result = result[result["ARR"] >= min_arr].sort_values(
        ["risk_rank", "v32_false_positive_complaints", "ARR"], ascending=[False, False, False]
    ).head(bounded_limit(limit))
    columns = ["customer_id", "customer_name", "customer_segment", "ARR", "latest_retention_risk",
               "average_uptime", "minimum_uptime", "monthly_api_volume", "v32_ticket_count", "v32_false_positive_complaints"]
    records = result[columns].round({"average_uptime": 5, "minimum_uptime": 5, "monthly_api_volume": 0}).to_dict("records")
    return to_json(
        {"status": "ok", "definition": "High-value customer risk signals; not a causal churn model",
         "sample_size": int((customers["ARR"] >= min_arr).sum()),
         "time_period": {"usage_start": recent["usage_month"].min().date().isoformat(), "usage_end": latest_month.date().isoformat(),
                         "ticket_model_period": "v3.2"},
         "filters": {"min_arr": min_arr}, "results": records}
    )
