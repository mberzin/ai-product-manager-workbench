"""User-facing Product Manager Orchestrator for the Phase 5 specialist team."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from agents import Agent

from rag import load_vector_store_id


AGENTS_DIR = Path(__file__).resolve().parent


def _load_builder(filename: str, builder_name: str):
    """Load local agent modules without shadowing the SDK's `agents` package."""
    module_path = AGENTS_DIR / filename
    module_name = f"callguard_{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load specialist module at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, builder_name)


build_data_analyst_agent = _load_builder("data_analyst.py", "build_data_analyst_agent")
extract_data_analyst_output = _load_builder(
    "data_analyst.py", "extract_data_analyst_output"
)
build_product_strategist_agent = _load_builder(
    "product_strategist.py", "build_product_strategist_agent"
)
build_technical_pm_agent = _load_builder("technical_pm.py", "build_technical_pm_agent")


PRODUCT_MANAGER_INSTRUCTIONS = """
You are the senior Product Manager Orchestrator for the fictional CallGuard AI
company. You own the final user-facing answer and may consult three specialists as
tools. Specialists receive only the focused task you send them, so include the
question and necessary context in each delegation.

Route by the user's requested outcome, not merely by keywords in the topic:
- Descriptive company or product knowledge -> Product Strategist.
- Quantitative diagnosis or prioritization -> Data Analyst. This includes ranking
  customers or accounts using ARR, retention risk, uptime, complaints, usage, model
  quality, or other measured signals.
- Technical architecture, implementation, feasibility, rollout mechanics,
  engineering sequencing, or mitigation design -> Technical Product Manager.
- Business or product decisions that require both measured evidence and company
  strategy -> Data Analyst + Product Strategist.
- Use all three only when the requested decision genuinely requires quantitative,
  strategic, and technical perspectives to produce the requested deliverable.
- Use no specialist for simple general PM guidance that needs neither CallGuard
  evidence nor specialist expertise.

Avoid unnecessary calls. A focused quantitative question normally needs only the
Data Analyst. A focused company/persona question normally needs only the Product
Strategist. Consult multiple specialists only when their distinct evidence materially
changes a consequential recommendation. Never call all specialists by default.
Do not invoke a specialist simply because it could add interesting context. Prefer
the smallest set that can answer the actual question with sufficient evidence,
clear decision quality, lower latency, and lower token usage.

Distinguish diagnosis from decision-making:
- A request to explain what changed, identify a measurable spike, or rank affected
  accounts is a quantitative diagnosis; use the Data Analyst unless the user also
  requests business/customer implications.
- A company-level request to decide whether to launch, roll back, continue, stop,
  or prioritize a product investment—or to judge whether measured usage represents
  customer value—is a business/product decision. When it depends on CallGuard data,
  consult both Data Analyst and Product Strategist so the answer combines measured
  impact with documented strategy and customer priorities.
- Product rollout posture is a strategic decision; rollout mechanics are technical.
  Do not treat the former as sufficient reason to invoke the Technical Product Manager.
- When a request combines a measured reliability, latency, or technical regression
  with operational roadmap reprioritization or engineering sequencing, use all three:
  Data Analyst for magnitude, Product Strategist for roadmap/business priorities,
  and Technical Product Manager for architecture, feasibility, sequencing, and
  operational tradeoffs. A purely descriptive roadmap question remains Product
  Strategist-only.

For purely descriptive company or product knowledge—such as personas, target
customers, strategy priorities, or roadmap priorities—normally consult only the
Product Strategist. Do not consult the Data Analyst merely to embellish a retrieved
answer with unrelated metrics. Add quantitative analysis only when the user's actual
question or decision requires calculated evidence. Add the Technical Product Manager
only when architecture, implementation, reliability mitigation, or engineering
tradeoffs are explicitly relevant.

An incident, model version, complaint spike, reliability metric, or rollback topic
does not by itself require the Technical Product Manager. For a quantitative
diagnosis, use the Data Analyst first. For a high-level rollback or prioritization
decision, Data Analyst + Product Strategist are normally sufficient. Add the
Technical Product Manager only when the user asks for technical feasibility,
architecture, implementation risk, rollout mechanics, engineering sequencing,
technical root-cause investigation, or mitigation design—or when such detail is
indispensable to the requested deliverable.

Similarly, do not add the Product Strategist to a quantitative diagnosis merely
because customer or business context exists. Add that specialist when the user asks
for customer/business implications, personas, strategic-account importance, market
strategy, business positioning, roadmap, or a product-priority decision.

Mandatory evidence gate: before recommending a model rollback, incident mitigation,
or evidence-based product reprioritization, consult the Data Analyst. If the decision
also asks for customer strategy or the explicit technical dimensions listed above,
consult the relevant additional specialist(s). Do not make a rollback recommendation while saying the
quantitative evidence is unavailable when the Data Analyst can calculate it.

Synthesize findings into one concise PM answer; do not paste specialist responses.
Resolve disagreements where the evidence allows, and explicitly name unresolved
tradeoffs otherwise. Distinguish:
- Calculated evidence from deterministic analysis.
- Retrieved knowledge from allowlisted company documents, naming filenames when
  specialists provide them.
- Hypotheses or interpretations that still require validation.
- Your final recommendation and prioritized next steps.

Never invent metrics, company strategy, architecture, customer facts, or root cause.
Preserve the terminology, metric definitions, and filters in specialist evidence.
Do not use "complaints" as a synonym for "support tickets": unfiltered
support_ticket_count, ticket_count, or v32_ticket_count values from customer-support
tools must be described as support tickets. Interpret sample_size from its own tool
definition and filters rather than assuming it is a complaint count. Never relabel
unfiltered support-ticket totals as complaint counts. Use complaint language only when an explicit
complaint_type filter or explicitly named complaint metric establishes that subset,
and name the category so it remains distinct from other support-ticket categories.
Calibrate causal wording throughout the answer. Unless causal evidence exists, say
"strongly associated with," "consistent with," "likely contributor," or "evidence
suggests" rather than presenting causality strongly and adding a later disclaimer.
Do not claim causality from correlation or release timing alone. Cite the specific
values, sample sizes, periods, segments, and retrieved sources that support the
answer. Keep the final response concise, practical, and PM-oriented.
""".strip()


def build_product_manager_agent(
    vector_store_id: str | None = None,
    specialist_hooks=None,
) -> Agent:
    """Build the orchestrator and its three least-privilege specialist tools."""
    configured_id = vector_store_id if vector_store_id is not None else load_vector_store_id()
    data_analyst = build_data_analyst_agent()
    product_strategist = build_product_strategist_agent(configured_id)
    technical_pm = build_technical_pm_agent(configured_id)

    specialist_tools = [
        data_analyst.as_tool(
            tool_name="consult_data_analyst",
            tool_description=(
                "Consult the Data Analyst for deterministic quantitative evidence about model "
                "performance, complaints, customer risk, latency, uptime, feature usage, or "
                "experiments. Use this specialist for account prioritization based on ARR, "
                "retention risk, uptime, complaints, or usage. Always use for evidence-based "
                "rollback decisions. For focused "
                "quantitative questions, do not call other specialists unless needed. Do not "
                "use for purely descriptive personas, strategy, target-customer, or roadmap "
                "questions that require no calculated evidence."
            ),
            custom_output_extractor=extract_data_analyst_output,
            max_turns=8,
            hooks=specialist_hooks,
        ),
        product_strategist.as_tool(
            tool_name="consult_product_strategist",
            tool_description=(
                "Consult the Product Strategist for retrieved CallGuard personas, customer "
                "priorities, product strategy, roadmap context, and business tradeoffs. Use "
                "this specialist alone for purely descriptive company and product knowledge "
                "unless the question itself requires quantitative or technical evidence. Use "
                "with the Data Analyst for company-level product decisions about investment, "
                "customer value, launch, continuation, prioritization, or rollout posture. Do "
                "not use for account ranking based only on measured risk signals."
            ),
            max_turns=6,
            hooks=specialist_hooks,
        ),
        technical_pm.as_tool(
            tool_name="consult_technical_pm",
            tool_description=(
                "Consult the Technical Product Manager for documented architecture, API, model "
                "rollout mechanics, technical mitigation design, implementation feasibility, "
                "operational risk, and engineering tradeoffs. Use only when the requested "
                "answer needs those technical dimensions. A model, incident, complaint, "
                "reliability, or rollback topic alone is not sufficient reason to call this "
                "specialist. Do use when a measured technical or reliability regression is "
                "being combined with operational roadmap reprioritization or engineering "
                "sequencing."
            ),
            max_turns=6,
            hooks=specialist_hooks,
        ),
    ]
    return Agent(
        name="Product Manager Orchestrator",
        instructions=PRODUCT_MANAGER_INSTRUCTIONS,
        tools=specialist_tools,
    )


product_manager_agent = build_product_manager_agent()
