# POST /api/v1/chat/customer — plan.txt section 5 (Customer chatbot) + section 7 (API contract)
#
# TODO:
#   - Authorization header OPTIONAL (guest = product search + RAG only;
#     logged-in = also gets order tools, scoped via app.deps.auth)
#   - body: {conversation_id: str | None, message: str}
#   - stream response as text/event-stream (SSE) from app.agents.customer.graph
#   - persist conversation/messages via app.db.ai_models
