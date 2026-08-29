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

There is intentionally no multi-agent flow, handoff, authentication, external
database, LangChain, LlamaIndex, or deployment configuration.

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
metadata, never chain-of-thought.

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

## Project status

This is **Phase 5**: one Product Manager Orchestrator, three least-privilege
specialists, one chat interface, a fully synthetic company and dataset,
deterministic analytical tools, and OpenAI File Search over a strictly allowlisted
synthetic knowledge base.

All company knowledge, customer records, metrics, incidents, and roadmap details in
this repository are synthetic and intended only for learning and evaluation.
