"""Production-facing analytical tools available to the Product Manager agent."""

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


PRODUCT_ANALYSIS_TOOLS = [
    compare_model_versions,
    calculate_precision,
    calculate_recall,
    calculate_false_positive_rate,
    segment_model_performance,
    analyze_complaint_trends,
    segment_complaints,
    identify_high_risk_customers,
    analyze_latency_by_region,
    analyze_uptime_by_customer,
    analyze_feature_usage,
    analyze_experiment,
    compare_experiment_segments,
]

__all__ = ["PRODUCT_ANALYSIS_TOOLS"]
