# AI Product Manager Workbench

AI Product Manager Workbench is a portfolio and learning project for exploring how
agentic AI can support product analysis and decision-making. In this first phase, a
senior B2B SaaS / AI Product Manager agent helps turn ambiguous product problems
into structured hypotheses, metrics, tradeoffs, and next steps.

## Current architecture

```text
Streamlit chat UI (app.py)
        |
        v
Product Manager agent (agents/product_manager.py)
        |
        v
Deterministic function tools (tools/)
        |
        v
Synthetic CallGuard AI CSVs (data/)
```

- `app.py` loads local environment variables, manages the visible chat history,
  and runs the agent.
- `agents/product_manager.py` contains the single agent, its evidence-aware
  instructions, and its analytical tool registration.
- The local `agents/` directory deliberately has no `__init__.py`, because the
  Agents SDK itself uses the Python package name `agents`. The app loads the local
  definition by file path to keep the requested layout without shadowing the SDK.
- `data/` contains the deterministic synthetic CallGuard AI dataset. Its
  developer-only ground-truth guide is not available to production tools.
- `knowledge/` documents the fictional company, personas, strategy, architecture,
  and roadmap for future phases.
- `tools/` contains read-only pandas analyses for model quality, complaints,
  customer risk, reliability, feature usage, and experiments.
- `tests/` covers the dataset and analytical tools without calling the OpenAI API.

There is intentionally no RAG, vector database, multi-agent flow, handoff,
authentication, or deployment configuration yet.

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

4. Start the app:

   ```powershell
   streamlit run app.py
   ```

5. Optionally run the tests:

   ```powershell
   python -m unittest discover -s tests
   ```

## Project status

This is **Phase 3**: one Product Manager agent, one simple chat interface, a fully
synthetic company dataset, and deterministic analytical tools. RAG and multi-agent
patterns remain intentionally out of scope.
