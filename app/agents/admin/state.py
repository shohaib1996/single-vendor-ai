# LangGraph state schema for the admin analytics agent — plan.txt
# section 6. Extends langchain.agents.AgentState (same as the customer
# agent — see agents/customer/state.py for why).

from langchain.agents import AgentState


class AdminAgentState(AgentState):
    user_id: str
