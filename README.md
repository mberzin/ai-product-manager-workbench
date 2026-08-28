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
OpenAI Agents SDK
```

- `app.py` loads local environment variables, manages the visible chat history,
  and runs the agent.
- `agents/product_manager.py` contains the single agent and its instructions.
- The local `agents/` directory deliberately has no `__init__.py`, because the
  Agents SDK itself uses the Python package name `agents`. The app loads the local
  definition by file path to keep the requested layout without shadowing the SDK.
- `data/`, `knowledge/`, and `tools/` are placeholders for later phases.
- `tests/` contains lightweight checks that do not call the OpenAI API.

There is intentionally no RAG, vector database, synthetic data, multi-agent flow,
handoff, analytics tooling, authentication, or deployment configuration yet.

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

This is **Phase 1**: one agent and one simple chat interface. The empty foundation
directories make future learning steps visible without implementing them early.
