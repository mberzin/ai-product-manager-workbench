# Developer Ground Truth: Embedded Product Scenarios

**Developer-only evaluation artifact. Do not expose this file to a production agent
or include it in a production retrieval index.** Every company, customer, and record
in this dataset is synthetic.

The generator uses random seed `20250828` and calendar year 2025.

## Scenario A — v3.2 recall / precision tradeoff

**Expected conclusion:** v3.2 materially increases binary unwanted-call recall but
reduces precision because more legitimate calls are classified as spam, fraud, or
robocall.

**Evidence:** `calls.csv` fields `actual_category`, `predicted_category`, and
`model_version`; calculated summaries in `model_versions.csv` fields
`unwanted_call_precision` and `unwanted_call_recall`.

## Scenario B — concentrated complaint increase

**Expected conclusion:** the post-v3.2 false-positive complaint spike is
disproportionately concentrated in the `Tier 1 Carrier` segment, especially the
fictional `CUST-001` / Northstar Mobile account. An aggregate-only response would
miss the account and segment concentration.

**Evidence:** `support_tickets.csv` fields `ticket_date`, `model_version`,
`complaint_type`, `customer_segment`, and `customer_id`; join `customers.csv` for
customer name and ARR.

## Scenario C — EU latency regression

**Expected conclusion:** EU mean latency rises materially after the fictional July
15 infrastructure change, while non-EU latency does not show the same step change.

**Evidence:** `calls.csv` fields `call_date`, `country`, and `latency_ms`;
`knowledge/roadmap.md` documents the release timing.

## Scenario D — high-ARR churn risk

**Expected conclusion:** `CUST-001` is a high-ARR enterprise carrier with high
retention risk after September, low uptime, and concentrated false-positive
complaints. It should receive urgent cross-functional attention.

**Evidence:** `customers.csv` fields `ARR`, `customer_segment`, and `account_status`;
`product_usage.csv` fields `uptime` and `retention_risk`; `support_tickets.csv` for
complaint evidence.

## Scenario E — high usage, low value

**Expected conclusion:** the explainability feature records many queries but very
few actioned explanations. Adoption alone should not justify further investment;
the team should validate whether it improves decisions or investigation outcomes.

**Evidence:** `product_usage.csv` fields `explainability_queries` and
`explanations_actioned`. The action rate is intentionally very low.

## Scenario F — aggregate experiment masks segment harm

**Expected conclusion:** `EXP-008` / Auto-block recommendations looks positive in
aggregate but is negative for the strategically important `Tier 1 Carrier` segment.
It should not be rolled out globally without segment-specific redesign or controls.

**Evidence:** `experiments.csv` fields `aggregate_lift`, `tier_1_carrier_lift`,
`primary_metric`, and `conclusion`.
