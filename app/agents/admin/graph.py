# LangGraph admin analytics agent — plan.txt section 6. Same shape as
# agents/customer/graph.py (langchain.agents.create_agent + MemorySaver —
# same "not durable yet" caveat applies, see plan.txt section 12), but no
# guest path (admin-only, enforced by app.deps.auth.get_current_admin
# before this graph ever runs) and no rag_search tool — analytics tools
# only.

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from app.agents.admin.prompts import SYSTEM_PROMPT
from app.agents.admin.state import AdminAgentState
from app.agents.admin.tools import build_admin_tools
from app.core.llm import get_admin_llm

_checkpointer = MemorySaver()


def build_admin_graph():
    tools = build_admin_tools()
    llm = get_admin_llm()
    return create_agent(
        llm,
        tools=tools,
        state_schema=AdminAgentState,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=_checkpointer,
    )
