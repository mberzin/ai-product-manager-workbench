"""Deterministic model-quality tools for the synthetic call dataset."""

from __future__ import annotations

from agents import function_tool

from tools.data_access import add_region, bounded_limit, error_result, load_data, time_period, to_json


UNWANTED = {"spam", "fraud", "robocall"}
VALID_DIMENSIONS = {"customer_segment", "country", "region", "carrier"}


def _calls_with_customers():
    calls = add_region(load_data("calls.csv"))
    customers = load_data("customers.csv")[["customer_id", "customer_segment"]]
    return calls.merge(customers, on="customer_id", how="left", validate="many_to_one")


def _filter_calls(model_version: str, customer_segment: str | None, country: str | None):
    calls = _calls_with_customers()
    if model_version not in set(calls["model_version"]):
        return None, f"Unknown model_version '{model_version}'. Use v3.0, v3.1, or v3.2."
    calls = calls[calls["model_version"] == model_version]
    if customer_segment:
        if customer_segment not in set(calls["customer_segment"]):
            return None, f"Unknown customer_segment '{customer_segment}'."
        calls = calls[calls["customer_segment"] == customer_segment]
    if country:
        if country not in set(calls["country"]):
            return None, f"Unknown country '{country}'."
        calls = calls[calls["country"] == country]
    return calls, None


def _confusion(calls):
    actual_unwanted = calls["actual_category"].isin(UNWANTED)
    predicted_unwanted = calls["predicted_category"].isin(UNWANTED)
    return {
        "true_positives": int((actual_unwanted & predicted_unwanted).sum()),
        "false_positives": int((~actual_unwanted & predicted_unwanted).sum()),
        "false_negatives": int((actual_unwanted & ~predicted_unwanted).sum()),
        "true_negatives": int((~actual_unwanted & ~predicted_unwanted).sum()),
    }


def _metric_payload(metric: str, model_version: str, customer_segment: str | None, country: str | None) -> str:
    calls, error = _filter_calls(model_version, customer_segment, country)
    if error:
        return error_result(error, tool_metric=metric)
    counts = _confusion(calls)
    if metric == "precision":
        numerator = counts["true_positives"]
        denominator = counts["true_positives"] + counts["false_positives"]
        definition = "TP / (TP + FP), treating spam, fraud, and robocall as unwanted"
    elif metric == "recall":
        numerator = counts["true_positives"]
        denominator = counts["true_positives"] + counts["false_negatives"]
        definition = "TP / (TP + FN), treating spam, fraud, and robocall as unwanted"
    else:
        numerator = counts["false_positives"]
        denominator = counts["false_positives"] + counts["true_negatives"]
        definition = "FP / (FP + TN), or legitimate calls predicted as unwanted / all legitimate calls"
    value = numerator / denominator if denominator else None
    return to_json(
        {
            "status": "ok", "metric": metric, "definition": definition,
            "value": round(value, 4) if value is not None else None,
            "sample_size": len(calls), "time_period": time_period(calls, "call_date"),
            "filters": {"model_version": model_version, "customer_segment": customer_segment, "country": country},
            "confusion_counts": counts,
        }
    )


@function_tool
def calculate_precision(
    model_version: str,
    customer_segment: str | None = None,
    country: str | None = None,
) -> str:
    """Calculate unwanted-call precision for one model, optionally filtered.

    Use when the user asks how often calls predicted as spam, fraud, or robocall
    were actually unwanted. Optional filters support a customer segment or country.
    """
    return _metric_payload("precision", model_version, customer_segment, country)


@function_tool
def calculate_recall(
    model_version: str,
    customer_segment: str | None = None,
    country: str | None = None,
) -> str:
    """Calculate unwanted-call recall for one model, optionally filtered.

    Use when the user asks what share of actual spam, fraud, and robocalls the model
    detected. Optional filters support a customer segment or country.
    """
    return _metric_payload("recall", model_version, customer_segment, country)


@function_tool
def calculate_false_positive_rate(
    model_version: str,
    customer_segment: str | None = None,
    country: str | None = None,
) -> str:
    """Calculate the legitimate-call false-positive rate for one model.

    Use when evaluating customer harm or whether a model is incorrectly classifying
    legitimate calls as spam, fraud, or robocall.
    """
    return _metric_payload("false_positive_rate", model_version, customer_segment, country)


@function_tool
def compare_model_versions() -> str:
    """Compare precision, recall, false-positive rate, and sample size for all models.

    Use for release comparisons, rollback questions, or understanding whether a
    quality gain in one metric caused a tradeoff in another.
    """
    calls = _calls_with_customers()
    results = []
    for version in sorted(calls["model_version"].unique()):
        group = calls[calls["model_version"] == version]
        counts = _confusion(group)
        precision = counts["true_positives"] / (counts["true_positives"] + counts["false_positives"])
        recall = counts["true_positives"] / (counts["true_positives"] + counts["false_negatives"])
        fpr = counts["false_positives"] / (counts["false_positives"] + counts["true_negatives"])
        results.append(
            {"model_version": version, "precision": round(precision, 4), "recall": round(recall, 4),
             "false_positive_rate": round(fpr, 4), "sample_size": len(group),
             "time_period": time_period(group, "call_date")}
        )
    return to_json(
        {"status": "ok", "metric_definitions": {
            "precision": "TP / (TP + FP)", "recall": "TP / (TP + FN)",
            "false_positive_rate": "FP / (FP + TN)",
        }, "results": results}
    )


@function_tool
def segment_model_performance(
    model_version: str,
    dimension: str = "customer_segment",
    limit: int = 10,
) -> str:
    """Compare model quality across customer segment, country, region, or carrier.

    Use to detect concentrated model impact that aggregate metrics may hide.
    Results are sorted by false-positive rate and capped to a small number of rows.
    """
    if dimension not in VALID_DIMENSIONS:
        return error_result(f"Invalid dimension '{dimension}'.", allowed_dimensions=sorted(VALID_DIMENSIONS))
    calls, error = _filter_calls(model_version, None, None)
    if error:
        return error_result(error)
    rows = []
    for value, group in calls.groupby(dimension, dropna=False):
        counts = _confusion(group)
        precision_denominator = counts["true_positives"] + counts["false_positives"]
        recall_denominator = counts["true_positives"] + counts["false_negatives"]
        fpr_denominator = counts["false_positives"] + counts["true_negatives"]
        rows.append(
            {dimension: str(value), "sample_size": len(group),
             "precision": round(counts["true_positives"] / precision_denominator, 4),
             "recall": round(counts["true_positives"] / recall_denominator, 4),
             "false_positive_rate": round(counts["false_positives"] / fpr_denominator, 4)}
        )
    rows.sort(key=lambda row: (-row["false_positive_rate"], -row["sample_size"]))
    return to_json(
        {"status": "ok", "model_version": model_version, "dimension": dimension,
         "metric_definitions": {"precision": "TP/(TP+FP)", "recall": "TP/(TP+FN)", "false_positive_rate": "FP/(FP+TN)"},
         "sample_size": len(calls), "time_period": time_period(calls, "call_date"),
         "results": rows[:bounded_limit(limit)]}
    )
