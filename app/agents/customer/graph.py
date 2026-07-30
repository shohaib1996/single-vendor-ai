# LangGraph StateGraph for the customer agent — plan.txt section 5
#
# entry (inject user_id/role from verified JWT, load prior turns from
#         checkpointer) -> agent (GPT w/ tools bound) -> tools (ToolNode)
#         -> respond -> guardrail
#
# TODO: wire nodes using langgraph.graph.StateGraph + this package's
# state.py / tools.py / prompts.py. Use a Postgres or Redis checkpointer
# (app.core.memory) for multi-turn conversation memory.
