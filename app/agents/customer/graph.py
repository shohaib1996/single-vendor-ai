# LangGraph customer agent — plan.txt section 5.
#
# Built with langchain.agents.create_agent (a StateGraph under the hood):
# agent node calls the LLM with tools bound, loops through tool calls,
# ends on a plain-text response. This is the standard, well-tested
# LangGraph ReAct pattern rather than a hand-rolled graph. (This used to
# be langgraph.prebuilt.create_react_agent — deprecated as of LangGraph
# v1.0 in favor of this langchain.agents version; same behavior, the
# `prompt` kwarg was just renamed `system_prompt`.)

from langchain.agents import create_agent

import app.core.memory as memory
from app.agents.customer.prompts import SYSTEM_PROMPT
from app.agents.customer.state import CustomerAgentState
from app.agents.customer.tools import build_customer_tools
from app.core.llm import get_customer_llm


def build_customer_graph(user_id: str | None):
    """Builds a graph scoped to the calling user (or None for a guest).

    Rebuilt per request rather than cached globally because the
    available tool set depends on user_id (see tools.py) — this keeps
    the user_id -> tool closure binding simple and unambiguous instead
    of threading it through LangGraph's runtime config. The checkpointer
    itself IS shared/cached (see core/memory.py) — only the graph
    wiring is rebuilt.
    """
    tools = build_customer_tools(user_id)
    llm = get_customer_llm()
    return create_agent(
        llm,
        tools=tools,
        state_schema=CustomerAgentState,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=memory.checkpointer,
    )
