# Phase 3 Agent Evaluation Questions

These evaluations should be run against the production-facing Product Manager
agent and analytical tools. The expected evidence below comes from CSV calculations;
the agent should discover it by calling tools, not by consulting developer-only
scenario documentation.

## 1. Why did customer complaints spike after model v3.2?

Expected tool path: `analyze_complaint_trends`, `segment_complaints`,
`compare_model_versions`, and optionally `segment_model_performance`.

Expected evidence: false-positive complaints rise in the v3.2 period; the increase
is heavily concentrated in Tier 1 carriers and the CUST-001 account; v3.2 has higher
recall but lower precision and a higher legitimate-call false-positive rate. The
agent may identify the model change as a supported contributor, but should not claim
it is the sole root cause without stronger causal evidence.

## 2. Should CallGuard roll back v3.2 globally?

Expected tool path: `compare_model_versions`, `segment_model_performance`, and
`segment_complaints`.

Expected evidence: v3.2 creates a real recall benefit and a real precision/FPR cost,
while complaint harm is concentrated. A global rollback is not automatically
supported; recommend a segmented mitigation, threshold adjustment, canary, or
targeted rollback while validating broader impact.

## 3. Which high-value customers are most at risk?

Expected tool path: `identify_high_risk_customers` and
`analyze_uptime_by_customer`.

Expected evidence: CUST-001 / Northstar Mobile combines high ARR, high retention
risk, degraded uptime, and many v3.2 false-positive complaints. The answer should
cite the account's calculated evidence and avoid presenting the flags as a churn
probability.

## 4. What happened to EU latency?

Expected tool path: `analyze_latency_by_region` with split date `2025-07-15`.

Expected evidence: EU mean and p95 latency increase materially after the split while
the tool reports both sample sizes and periods. Timing supports an association with
the infrastructure change, not proof of a specific technical root cause.

## 5. Is the explainability feature creating customer value?

Expected tool path: `analyze_feature_usage`.

Expected evidence: explainability has high query volume across customers but a very
low recorded action rate. This demonstrates adoption and weak measured action
conversion, not proof that the feature has no value; recommend outcome research or
an experiment tied to investigation quality and business results.

## 6. Is EXP-008 a successful experiment?

Expected tool path: `analyze_experiment` and `compare_experiment_segments`.

Expected evidence: aggregate lift is positive, but Tier 1 carrier lift is negative
and directionally conflicts with the aggregate. The agent should reject an
unqualified global-success conclusion and recommend segment-specific follow-up.
