"""Regional latency and customer uptime tools."""

from __future__ import annotations

import pandas as pd
from agents import function_tool

from tools.data_access import add_region, bounded_limit, date_filter, error_result, load_data, time_period, to_json


@function_tool
def analyze_latency_by_region(
    start_date: str | None = None,
    end_date: str | None = None,
    split_date: str | None = None,
) -> str:
    """Summarize latency by EU versus Non-EU region, optionally before/after a date.

    Use for regional latency regressions or infrastructure-change analysis. Returns
    mean, median, p95, sample size, and periods; it does not infer root cause.
    """
    calls = add_region(load_data("calls.csv"))
    calls, error = date_filter(calls, "call_date", start_date, end_date)
    if error:
        return error_result(error)
    if calls.empty:
        return error_result("No call records match the requested date range.")
    if split_date:
        try:
            split = pd.Timestamp(split_date)
        except (TypeError, ValueError):
            return error_result("split_date must use ISO format, for example 2025-07-15.")
        calls["period"] = calls["call_date"].apply(lambda value: "before" if value < split else "on_or_after")
        group_columns = ["region", "period"]
    else:
        group_columns = ["region"]
    grouped = calls.groupby(group_columns)["latency_ms"].agg(
        sample_size="count", mean_latency_ms="mean", median_latency_ms="median",
        p95_latency_ms=lambda values: values.quantile(0.95),
    ).reset_index()
    for column in ["mean_latency_ms", "median_latency_ms", "p95_latency_ms"]:
        grouped[column] = grouped[column].round(1)
    return to_json(
        {"status": "ok", "metric_definition": "Call-level API latency in milliseconds; p95 is the 95th percentile",
         "sample_size": len(calls), "time_period": time_period(calls, "call_date"),
         "filters": {"start_date": start_date, "end_date": end_date, "split_date": split_date},
         "results": grouped.to_dict("records")}
    )


@function_tool
def analyze_uptime_by_customer(
    customer_id: str | None = None,
    risk_only: bool = False,
    limit: int = 10,
) -> str:
    """Summarize monthly uptime by customer with ARR and retention-risk context.

    Use for reliability, SLA, or account-risk analysis. Returns the lowest-uptime
    customers first and never returns the full monthly usage table.
    """
    usage = load_data("product_usage.csv")
    customers = load_data("customers.csv")[["customer_id", "customer_name", "customer_segment", "ARR"]]
    if customer_id and customer_id not in set(usage["customer_id"]):
        return error_result(f"Unknown customer_id '{customer_id}'.")
    if customer_id:
        usage = usage[usage["customer_id"] == customer_id]
    if risk_only:
        usage = usage[usage["retention_risk"].isin(["high", "medium"])]
    if usage.empty:
        return error_result("No uptime records match the requested filters.")
    summary = usage.groupby("customer_id").agg(
        average_uptime=("uptime", "mean"), minimum_uptime=("uptime", "min"),
        months_observed=("usage_month", "count"), high_risk_months=("retention_risk", lambda values: int((values == "high").sum())),
    ).reset_index().merge(customers, on="customer_id", how="left")
    summary = summary.sort_values(["minimum_uptime", "ARR"], ascending=[True, False]).head(bounded_limit(limit))
    summary[["average_uptime", "minimum_uptime"]] = summary[["average_uptime", "minimum_uptime"]].round(5)
    columns = ["customer_id", "customer_name", "customer_segment", "ARR", "average_uptime", "minimum_uptime", "months_observed", "high_risk_months"]
    return to_json(
        {"status": "ok", "metric_definition": "Monthly uptime fraction from product_usage.csv; 0.99 means 99%",
         "sample_size": len(usage), "time_period": time_period(usage, "usage_month"),
         "filters": {"customer_id": customer_id, "risk_only": risk_only},
         "results": summary[columns].to_dict("records")}
    )
