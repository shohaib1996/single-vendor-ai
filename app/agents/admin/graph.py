# LangGraph StateGraph for the admin analytics agent — plan.txt section 6
#
# TODO: same shape as app/agents/customer/graph.py but no guest path (this
# endpoint is admin-only, enforced by app.deps.auth.get_current_admin
# before the graph ever runs) and no rag_search tool — analytics tools only.
