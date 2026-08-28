# CallGuard AI High-Level Architecture

## Request path

1. A customer sends call metadata to a regional API endpoint.
2. The API gateway authenticates the tenant, applies rate limits, and attaches the
   customer policy configuration.
3. A feature service retrieves number, carrier, traffic-pattern, and reputation
   features from low-latency stores.
4. The active model scores the call and returns category probabilities.
5. A policy layer converts the model output into a category and optional action such
   as label, allow, challenge, or block.
6. The response includes the predicted category, confidence, model version, and
   selected reason codes.
7. Events flow asynchronously to monitoring, analytics, evaluation, and billing.

## Regional operation

Traffic is served from US and EU regions with regional feature caches. A routing
layer selects the closest healthy inference cluster. Because a routing or cache
change can affect one region without changing global averages, latency and error
budgets are monitored by region, customer segment, and customer.

## Model lifecycle

Models are trained offline on synthetic labels in this project (production data is
not present). A release progresses through offline evaluation, shadow traffic,
limited canary, segment review, and staged rollout. Precision, recall, false-positive
rate, complaints, latency, and customer-level guardrails determine promotion or
rollback.

## Scope boundary

This document is conceptual context only. Phase 2 does not implement these services,
data pipelines, model training, infrastructure, or RAG.
