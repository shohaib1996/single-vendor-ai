# LangGraph state schema for the customer agent — plan.txt section 5.
# Extends create_agent's own AgentState (langchain.agents — the
# langgraph.prebuilt.create_react_agent this used to build on is
# deprecated as of LangGraph v1.0) with the two fields every tool/prompt
# needs: user_id comes from the verified JWT (app.deps.auth), never from
# chat text — see the security note in tools.py.

from langchain.agents import AgentState


class CustomerAgentState(AgentState):
    user_id: str | None
    role: str | None
