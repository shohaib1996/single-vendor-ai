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
from langgraph.checkpoint.memory import MemorySaver

from app.agents.customer.prompts import SYSTEM_PROMPT
from app.agents.customer.state import CustomerAgentState
from app.agents.customer.tools import build_customer_tools
from app.core.llm import get_customer_llm

# TODO: swap for a durable Postgres/Redis checkpointer (plan.txt section 5
# / section 12) once the `ai_chat` schema exists. MemorySaver keeps
# conversation state only in this process's memory — fine for local
# testing, but it's lost on restart and won't work across multiple
# server workers.
_checkpointer = MemorySaver()


def build_customer_graph(user_id: str | None):
    """Builds a graph scoped to the calling user (or None for a guest).

    Rebuilt per request rather than cached globally because the
    available tool set depends on user_id (see tools.py) — this keeps
    the user_id -> tool closure binding simple and unambiguous instead
    of threading it through LangGraph's runtime config.
    """
    tools = build_customer_tools(user_id)
    llm = get_customer_llm()
    return create_agent(
        llm,
        tools=tools,
        state_schema=CustomerAgentState,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=_checkpointer,
    )
