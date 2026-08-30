# AI Product Manager Workbench Demo Guide

## Recommended featured question

> Should we roll back v3.2 specifically for Tier 1 carriers? Consider model
> performance, customer strategy, and technical mitigation options.

This is the strongest full-system demo because the decision needs calculated model
and complaint evidence, retrieved customer/strategy context, and technical rollout
tradeoffs. The orchestrator should selectively combine all three specialists and
still deliver one PM recommendation.

## Three-minute flow

1. **Set context (30 seconds).** Explain that CallGuard AI is fictional and all data
   is synthetic. The goal is evidence-grounded PM decision support, not autonomous
   decision-making.
2. **Run the featured question (90 seconds).** Select the featured example. While it
   runs, explain that the orchestrator chooses which specialists are materially useful.
3. **Review the answer (30 seconds).** Point out calculated facts, retrieved context,
   assumptions, tradeoffs, and the recommended next step.
4. **Open transparency (30 seconds).** Show Agents involved, Tools used, Knowledge
   used, and Execution metadata. Emphasize that these are execution facts—not hidden
   reasoning or chain-of-thought.

## Five-minute flow

1. Give the same 30-second framing.
2. Run **“What happened to EU latency?”** to show a focused quantitative question and
   minimal delegation.
3. Run **“Who are CallGuard's main personas and what matters most to them?”** to show
   retrieval-only product knowledge.
4. Run or show the featured Tier 1 rollback scenario to explain cross-functional
   synthesis.
5. Close with the evaluation results and limitations below.

If live API time is tight, run only the featured scenario and describe how the two
focused examples exercise narrower paths.

## What to point out

- **Agents involved:** delegation follows user intent; specialists are not called just
  because they might add interesting context.
- **Tools used:** pandas calculates metrics deterministically, with filters, periods,
  and sample sizes suitable for audit.
- **Knowledge used:** filenames show which allowlisted synthetic documents supported
  qualitative context.
- **Execution metadata:** latency and SDK token usage expose real operational tradeoffs.

## Architecture talking points

- A manager-style Product Manager Orchestrator owns the final response.
- Data Analyst permissions are limited to read-only synthetic CSV tools.
- Product Strategist and Technical PM retrieve only scoped synthetic knowledge.
- Structured analytics and RAG solve different evidence problems.
- Evaluation is isolated from production; ground truth never enters an agent prompt.

## Evaluation talking points

- Twelve cases cover quantitative, retrieval, and cross-functional decisions.
- Phase 6.2 stability runs reached 100% routing coverage and about 95.8% routing
  precision, with approximately 95.8%–100% evidence coverage.
- Average latency was about 15.6–16.0 seconds, with zero analytical tool failures.
- Running the same suite twice exposed variability in qualitative synthesis; the
  project reports that variability instead of averaging it away.
- The suite is synthetic and does not establish production reliability.

## Limitations and tradeoffs to volunteer

- Multi-agent depth improves separation of responsibility but increases latency,
  tokens, cost, and failure surface.
- Routing and prose synthesis remain model-dependent and nondeterministic.
- Session request limits reduce casual public abuse but are not identity-based quotas.
- There is no authentication, persistent memory, real customer data, or human approval
  workflow.
- Retrieval-source visibility is useful but not a complete trace of hosted retrieval.
- A production version would need monitoring, budgets, access controls, privacy review,
  semantic evaluation, and explicit decision ownership.
