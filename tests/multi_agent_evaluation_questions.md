# Phase 5 Multi-Agent Evaluations

These live evaluations verify selective delegation. The orchestrator should consult
only specialists whose distinct evidence materially improves the answer, then return
one concise PM synthesis rather than concatenated specialist reports.

## 1. What happened to EU latency?

- **Ideal specialists:** Data Analyst only.
- **Evidence:** `analyze_latency_by_region`, split around 2025-07-15, with EU mean,
  p95, sample sizes, and comparison to Non-EU traffic.
- **Strong conclusion:** EU latency materially regressed after the change window;
  timing supports investigation but does not establish a technical root cause.

## 2. Who are CallGuard's main personas?

- **Ideal specialists:** Product Strategist only.
- **Evidence:** retrieved persona roles and priorities from `personas.md`, supported
  by `company_overview.md` where useful.
- **Strong conclusion:** concise differentiation of carrier, bank, contact-center,
  communications-platform, trust-and-safety, and integration/SRE needs.

## 3. Should we roll back v3.2 globally?

- **Ideal specialists:** Data Analyst + Product Strategist. Technical PM only if the
  answer evaluates rollout mechanics rather than the product decision alone.
- **Evidence:** model precision/recall/FPR tradeoff, complaint concentration, and
  retrieved trust, segmentation, and reversible-rollout principles.
- **Strong conclusion:** a global rollback is not automatically supported because
  v3.2 improves recall and harm is concentrated; prioritize segmented mitigation and
  validation while protecting legitimate calls.

## 4. Should we roll back v3.2 specifically for Tier 1 carriers?

- **Ideal specialists:** Data Analyst + Product Strategist; Technical PM is useful
  for threshold, policy-layer, canary, and rollback options.
- **Evidence:** Tier 1 complaint/model impact, relevant customer priorities and
  strategy, plus documented architecture and reversible rollout mechanisms.
- **Strong conclusion:** consider a targeted rollback or threshold mitigation with
  carrier-specific guardrails rather than assuming one global response.

## 5. Should CallGuard prioritize fixing v3.2 or continuing investment in explainability?

- **Ideal specialists:** Data Analyst + Product Strategist. Technical PM only if
  sequencing or implementation capacity is central to the request.
- **Evidence:** v3.2 quality/customer harm, explainability query-to-action rate, and
  retrieved strategy that prioritizes trust and outcomes over adoption.
- **Strong conclusion:** address active v3.2 trust harm first while limiting
  explainability work to an outcome-linked validation experiment.

## 6. Design a mitigation plan for the v3.2 false-positive problem that minimizes customer harm without giving up all recall gains.

- **Ideal specialists:** Data Analyst + Product Strategist + Technical PM.
- **Evidence:** aggregate and segmented model/complaint results, customer trust and
  strategy, and architecture facts about policy configuration, thresholds, staged
  rollout, monitoring, and rollback.
- **Strong conclusion:** a staged, segment-aware mitigation with measurable
  precision/recall and complaint guardrails, reversible rollout, customer
  communication, and explicit unknowns—not an unsupported root-cause claim.

## 7. Given the EU latency regression and current roadmap, what should CallGuard reprioritize?

- **Ideal specialists:** Data Analyst + Product Strategist + Technical PM.
- **Evidence:** regional latency magnitude and period, roadmap priorities, regional
  routing architecture, reliability implications, and high-value account risk.
- **Strong conclusion:** elevate EU latency restoration and regional resilience,
  sequence conflicting roadmap work explicitly, and protect affected renewals while
  engineering validates the technical cause.
