# Interview Talking Points

## Why did you build this?

I wanted to test whether an AI Product Manager could move beyond generic advice and
support an ambiguous product decision with inspectable evidence. The project let me
practice product framing, system design, synthetic data design, evaluation, and the
latency/cost/quality tradeoffs of agentic workflows.

## Why use multiple agents?

The domains need different evidence and permissions. A Data Analyst should calculate
metrics, a Product Strategist should retrieve company context, and a Technical PM
should assess architecture and rollout tradeoffs. Selective delegation makes those
responsibilities visible while the orchestrator remains accountable for synthesis.
The downside is more model calls, latency, tokens, and routing complexity.

## Why not let the LLM calculate metrics itself?

Language models are good at interpretation but unreliable calculators over thousands
of rows. pandas tools make definitions, filters, samples, and outputs repeatable and
testable. The model reasons from those results instead of inventing or approximating
company metrics.

## Why use RAG?

Product decisions need company-specific strategy, personas, roadmap, and architecture.
RAG retrieves only relevant passages at request time, so the agent need not memorize
or fabricate that context. The source filename also gives the user a basic provenance
signal.

## Why not put the CSVs into the vector store?

Vector search is suited to semantic retrieval, not exact aggregation. Embedding raw
rows would increase cost and reduce numerical auditability. CSVs stay behind
deterministic tools; narrative knowledge goes into the vector store.

## How did you evaluate the system?

I created 12 synthetic cases with expected specialists, evidence families, knowledge
sources, conclusions, and uncertainty requirements. Lifecycle hooks capture actual
calls, latency, failures, and token usage. Deterministic scoring measures routing and
evidence, while an optional model judge assesses qualitative PM synthesis separately.

## What failures did you find?

Live evaluations found over-delegation, a time-series latency result that was not
reliably propagated into synthesis, overconfident causal wording, and a stale case
expectation that contradicted the intended routing policy. Repeated runs also showed
that correct routing does not eliminate variability in final prose and evidence use.

## How did evaluation change the product?

It shifted routing from “collect every potentially useful perspective” toward minimum
sufficient delegation. It also led to clearer causal calibration, stronger propagation
of successful analytical results, and alignment between evaluation definitions and
the documented production policy. Those were targeted changes, not question-specific
answer hard-coding.

## What are the latency and cost tradeoffs?

A focused request may need one specialist; a cross-functional decision may need all
three. Each specialist adds model requests and tokens, while hosted retrieval adds its
own service work. The Phase 6.2 suite averaged roughly 15.6–16.0 seconds. In production
I would set budgets, cache safe context, stream observable progress, use smaller models
where quality holds, and measure whether each additional call improves decisions.

## What would you improve for production?

I would add authentication, server-side identity quotas, durable audit records,
monitoring and alerting, privacy/security review, model and prompt versioning, richer
semantic evaluations, human approval for consequential actions, cost controls, and a
real deployment pipeline. I would validate the system on permissioned real-world data
only after governance and data agreements were in place.

## What did Codex do versus what decisions did you make?

I defined the product goals, scope, synthetic scenarios, routing principles,
evaluation expectations, safety constraints, and tradeoff decisions. Codex served as
an implementation and coding agent: it translated requirements into repository
changes, ran tests, inspected failures, and iterated with me. It accelerated execution;
it did not independently own all product or architecture decisions.
