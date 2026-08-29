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
Product Manager agent (agents/product_manager.py)
        |                         |
        v                         v
Deterministic tools        OpenAI File Search
        |                         |
        v                         v
Synthetic CSVs             Vector store
                                  |
                                  v
                         Allowlisted knowledge/*.md
```

- `app.py` loads local environment variables, manages the visible chat history,
  and runs the agent.
- `agents/product_manager.py` contains the single agent, its evidence-aware
  instructions, analytical tools, and conditional File Search registration.
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

## RAG and analytical tools

Retrieval-augmented generation (RAG) lets the agent search a small OpenAI vector
store for relevant company context before answering. Use it for CallGuard's mission,
personas, strategy, architecture, roadmap, and release context.

RAG is different from the deterministic pandas tools:

- **File Search** retrieves relevant passages from synthetic Markdown knowledge and
  helps the agent explain qualitative context.
- **Analytical tools** calculate reproducible metrics from synthetic CSVs and return
  definitions, filters, sample sizes, and time periods.

The agent is instructed to combine both when a decision requires company priorities
and quantitative evidence, and to distinguish retrieved facts, calculated facts,
and hypotheses.

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

This is **Phase 4**: one Product Manager agent, one chat interface, a fully synthetic
company and dataset, deterministic analytical tools, and OpenAI File Search over a
strictly allowlisted synthetic knowledge base. Multi-agent patterns remain out of
scope.

All company knowledge, customer records, metrics, incidents, and roadmap details in
this repository are synthetic and intended only for learning and evaluation.
