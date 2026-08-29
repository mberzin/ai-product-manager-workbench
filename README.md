# AI Product Manager Workbench

AI Product Manager Workbench is a portfolio and learning project for exploring how
agentic AI can support product analysis and decision-making. A senior B2B SaaS / AI
Product Manager agent turns ambiguous product problems into structured evidence,
hypotheses, tradeoffs, and next steps for the fictional CallGuard AI company.

## Current architecture

```text
Streamlit chat UI (app.py)
        |
        v
Streamlit chat UI
        |
        v
Product Manager Orchestrator
        |
        +--> Data Analyst ------------> 13 deterministic pandas tools --> synthetic CSVs
        |
        +--> Product Strategist ------> scoped OpenAI File Search
        |
        +--> Technical Product Manager -> scoped OpenAI File Search
                                                |
                                                v
                                  allowlisted synthetic knowledge/*.md

Separate evaluation path (never imported by production agents):
evaluation/cases.json -> evaluation runner -> deterministic scoring -> local results
                                      +----> optional LLM judge
```

- `app.py` loads local environment variables, manages the visible chat history,
  and runs the agent.
- `agents/product_manager.py` contains the user-facing orchestrator and its three
  agent-as-tool delegations.
- `agents/data_analyst.py` owns quantitative analysis and the 13 deterministic
  pandas tools.
- `agents/product_strategist.py` owns personas, strategy, roadmap, customer, and
  business context through scoped File Search.
- `agents/technical_pm.py` owns architecture, API, rollout, reliability, and
  engineering tradeoffs through scoped File Search.
- The local `agents/` directory deliberately has no `__init__.py`, because the
  Agents SDK itself uses the Python package name `agents`. The app loads the local
  definition by file path to keep the requested layout without shadowing the SDK.
- `data/` contains the deterministic synthetic CallGuard AI dataset. Its
  developer-only ground-truth guide is not available to production tools.
- `knowledge/` documents the fictional company, personas, strategy, architecture,
  and roadmap. Only five explicitly allowlisted Markdown files are indexed.
- `rag/config.py` defines the indexing allowlist and validates the local vector-store
  configuration in `config/vector_store.json`.
- `scripts/setup_knowledge_base.py` creates or reuses the OpenAI vector store and
  skips unchanged uploads on subsequent runs.
- `tools/` contains read-only pandas analyses for model quality, complaints,
  customer risk, reliability, feature usage, and experiments.
- `tests/` covers the dataset and analytical tools without calling the OpenAI API.
- `evaluation/` contains the Phase 6 case dataset, lifecycle instrumentation,
  deterministic scoring, optional model-based judge, pricing configuration, and
  ignored local results. Evaluation code is separate from answer generation.

There are intentionally no handoffs, authentication, external database, LangChain,
LlamaIndex, or deployment configuration.

## Specialization and delegation

Phase 5 replaces Phase 4's single agent with a manager-style orchestration pattern.
Specialists are exposed to the Product Manager as tools, so the orchestrator remains
in control of the conversation and final answer; specialists never take over through
a handoff.

The orchestrator delegates only when specialist evidence materially improves the
answer:

- Focused quantitative questions normally use only the Data Analyst.
- Persona, customer, strategy, or roadmap questions normally use only the Product
  Strategist.
- Architecture, rollout, API, and engineering-risk questions use the Technical PM.
- Consequential cross-functional decisions may use two or three specialists.
- General PM guidance may need no specialist.

Specialization keeps permissions clear and outputs focused, but each specialist call
adds model requests, latency, and API cost. The orchestrator is explicitly instructed
not to call every specialist by default. Streamlit shows public agent names and tool
metadata, response latency, and actual SDK token usage when available—never
chain-of-thought.

## Evaluation and observability

Phase 6 adds a repeatable evaluation layer because an agentic answer can sound
reasonable while routing inefficiently, missing evidence, or making unsupported
claims. The checked-in dataset contains 12 representative quantitative, retrieval,
and cross-functional decisions.

Phase 6.2 aligns the complaint-spike case with the production intent policy: a
plain diagnostic question requires Data Analyst only. Product Strategist becomes
required only when strategic or customer implications are requested, and Technical
PM only when technical cause, architecture, rollout mechanics, or mitigation is in
scope. This corrects a stale routing expectation without changing the case's
quantitative evidence, conclusion, uncertainty, or causality checks.

Deterministic evaluation scores objective behavior:

- required and unnecessary specialist calls;
- routing coverage and precision;
- analytical tool-family and retrieved-source coverage;
- required evidence and conclusion characteristics using wording-tolerant checks;
- total latency, specialist calls, analytical calls, and successful/failed calls;
- actual input, output, and total token usage exposed by the Agents SDK.

The optional LLM judge scores recommendation quality, uncertainty, unsupported
causality, synthesis, and PM judgment from 1–5. These scores are explicitly
model-based opinions, not objective ground truth, and never modify the production
response.

`evaluation/ground_truth.py` is the only intentional access path for the developer
guide in `data/ground_truth.md`. Production code under `app.py`, `agents/`, `rag/`,
and `tools/` neither imports nor references that guide. The evaluation runner does
not add expected answers or ground truth to production-agent prompts.

The SDK provides aggregate token usage for nested agent runs. Cost estimation is
disabled unless explicit rates are added to the single configuration file
`evaluation/pricing.json`; reported costs are always labeled estimates. Nested
hosted File Search calls are not exposed through local tool hooks, so retrieval-call
count uses retrieval-specialist invocations as a documented proxy while source
coverage uses public filename citations.

## RAG and analytical tools

Retrieval-augmented generation (RAG) lets the agent search a small OpenAI vector
store for relevant company context before answering. Use it for CallGuard's mission,
personas, strategy, architecture, roadmap, and release context.

RAG is different from the deterministic pandas tools:

- **File Search** retrieves relevant passages from synthetic Markdown knowledge and
  helps the agent explain qualitative context.
- **Analytical tools** calculate reproducible metrics from synthetic CSVs and return
  definitions, filters, sample sizes, and time periods.

The orchestrator combines specialist findings when a decision requires company
priorities and quantitative evidence, distinguishing retrieved knowledge,
calculated evidence, hypotheses, and the final recommendation.

## Local setup

Python 3.13 is required.

1. Create and activate a virtual environment:

   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and add your API key locally:

   ```text
   OPENAI_API_KEY=your-key-here
   ```

   `.env` is ignored by Git. Never commit or share your API key.

4. Create or update the CallGuard knowledge vector store:

   ```powershell
   python scripts/setup_knowledge_base.py
   ```

   The script uploads only `company_overview.md`, `personas.md`,
   `product_strategy.md`, `architecture.md`, and `roadmap.md`. It stores only safe
   IDs and file hashes in `config/vector_store.json`; it never stores or prints the
   API key. Restart Streamlit after changing the vector-store configuration.

   As an alternative for hosted environments, set `CALLGUARD_VECTOR_STORE_ID` in
   the process environment to override the local config ID.

5. Start the app:

   ```powershell
   streamlit run app.py
   ```

6. Optionally run the tests:

   ```powershell
   python -m unittest discover -s tests
   ```

7. Run one live evaluation or the full suite:

   ```powershell
   python scripts/run_evaluations.py --case eu_latency_regression
   python scripts/run_evaluations.py
   ```

   Add `--judge` to enable the optional model-based qualitative evaluator. Results
   are written as JSON plus a Markdown summary under `evaluation/results/`; transient
   result files are ignored by Git. After adding explicit rates to
   `evaluation/pricing.json`, pass `--pricing-model <table-key>` to enable a clearly
   labeled estimate.

## Project status

This is **Phase 6**: one Product Manager Orchestrator, three least-privilege
specialists, one chat interface, a fully synthetic company and dataset,
deterministic analytical tools, and OpenAI File Search over a strictly allowlisted
synthetic knowledge base, plus a separate evaluation and observability layer.

Evaluation limitations include model-routing variability, wording-based evidence
checks that cannot prove semantic correctness, incomplete attribution of nested
hosted retrieval calls, and qualitative-judge subjectivity. Evaluation results
should guide investigation rather than serve as an infallible quality score.

All company knowledge, customer records, metrics, incidents, and roadmap details in
this repository are synthetic and intended only for learning and evaluation.
