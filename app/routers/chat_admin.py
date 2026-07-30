# POST /api/v1/chat/admin — plan.txt section 6 (Admin analytics chatbot) + section 7 (API contract)
#
# TODO:
#   - Authorization header REQUIRED, role must be ADMIN
#     -> use app.deps.auth.get_current_admin dependency
#   - body: {conversation_id: str | None, message: str}
#   - stream response as text/event-stream (SSE) from app.agents.admin.graph
#   - final SSE event may include an optional "chart": {type, data} field
