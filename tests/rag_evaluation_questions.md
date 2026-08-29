# Phase 4 Retrieval Evaluations

These evaluations require the configured production agent and the five allowlisted
CallGuard AI knowledge documents. Expected evidence names ordinary knowledge sources
and Phase 3 calculations; no developer-only evaluation artifact is needed.

## A. Who are CallGuard's primary customer personas and what do they care about?

Expected retrieval: `personas.md`, supported by `company_overview.md` where useful.
The answer should cover carrier product leaders, bank fraud leaders, contact-center
operations, communications-platform PMs, trust and safety analysts, and integration
engineers/SREs. It should synthesize their distinct quality, reliability,
explainability, control, and integration needs rather than quote the document.

## B. Based on CallGuard's strategy, which customer segment should receive the most attention during the v3.2 incident?

Expected retrieval: `product_strategy.md` and relevant customer principles from
`company_overview.md`. Expected calculation: `segment_complaints` and optionally
`identify_high_risk_customers`. A strong answer prioritizes Tier 1 carriers because
measured harm is concentrated there and strategy emphasizes trust, segmentation,
legitimate-call safety, and retention—not because every customer is equally harmed.

## C. How does the CallGuard API architecture affect mitigation options for the v3.2 false-positive problem?

Expected retrieval: `architecture.md` plus the v3.2 context in `roadmap.md`.
The answer should connect model scoring, the policy layer, confidence thresholds,
customer policy configuration, staged rollout, monitoring, and rollback mechanisms
to options such as per-customer thresholds, allowlists, targeted rollback, canaries,
and segment guardrails. It should not invent implementation details.

## D. Which current roadmap priorities could be impacted by the EU latency regression?

Expected retrieval: `roadmap.md`, with `architecture.md` for regional routing
context. Expected calculation: `analyze_latency_by_region`. The answer should connect
the measured EU regression with the “Now” latency work and later regional failover,
capacity automation, release guardrails, and high-value account protection.

## E. Given the quantitative evidence and company strategy, should CallGuard prioritize fixing v3.2 or investing in the explainability feature?

This question **requires both evidence types**.

- Retrieval: `product_strategy.md`, especially trust, legitimate-call safety,
  reliability, segmentation, and outcome-over-adoption principles.
- Calculations: `compare_model_versions`, `segment_complaints`, and
  `analyze_feature_usage`.

Expected synthesis: prioritize mitigating v3.2's measured precision/false-positive
harm for affected segments while preserving recall where possible. Explainability
has high usage but weak measured action conversion, so further investment needs a
clear outcome hypothesis rather than outranking an active trust incident.

## F. What tradeoffs should the PM consider before rolling back v3.2 for Tier 1 carriers?

This question **requires both evidence types**.

- Retrieval: `product_strategy.md` and `architecture.md` for trust principles,
  reversible rollout, per-customer policy, monitoring, and mitigation options.
- Calculations: `compare_model_versions`, `segment_model_performance`, and
  `segment_complaints`.

Expected synthesis: weigh recall gains against lower precision, false positives,
complaints, legitimate-call harm, operational complexity, and customer trust. A
targeted rollback or threshold change may reduce concentrated harm without giving up
v3.2's global recall benefit. Timing supports action but does not by itself prove a
single technical root cause.
