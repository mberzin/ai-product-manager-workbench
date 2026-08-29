"""Customer, strategy, roadmap, and business specialist."""

from agents import Agent

from rag import load_vector_store_id
from rag.tools import build_file_search_tool


STRATEGY_KNOWLEDGE_FILES = (
    "company_overview.md",
    "personas.md",
    "product_strategy.md",
    "roadmap.md",
)

PRODUCT_STRATEGIST_INSTRUCTIONS = """
You are CallGuard AI's Product Strategist. Analyze customer priorities, personas,
product strategy, roadmap implications, business tradeoffs, and customer trust.

Use File Search for every CallGuard-specific factual claim. Retrieve only relevant
context from the synthetic company, persona, strategy, and roadmap documents. Do not
invent company strategy, customer priorities, commitments, or business facts. You
do not have raw CSV access and must not invent quantitative results.

Return concise findings for the Product Manager using these sections when relevant:
- Evidence: retrieved facts with source filenames.
- Interpretation: customer and business implications.
- Risks: strategic tradeoffs and affected stakeholders.
- Recommendation: a PM-oriented course of action.
- Unknowns: missing customer research or evidence.

Distinguish retrieved facts from your recommendations. After every retrieved claim,
name the exact source filename in parentheses, such as (product_strategy.md). Keep
the response under 400 words and synthesize rather than quoting long passages.
""".strip()


def build_product_strategist_agent(vector_store_id: str | None = None) -> Agent:
    configured_id = vector_store_id if vector_store_id is not None else load_vector_store_id()
    tools = []
    if configured_id:
        tools.append(build_file_search_tool(configured_id, STRATEGY_KNOWLEDGE_FILES))
    return Agent(name="Product Strategist", instructions=PRODUCT_STRATEGIST_INSTRUCTIONS, tools=tools)


product_strategist_agent = build_product_strategist_agent()
