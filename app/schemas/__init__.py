# Pydantic request/response models — plan.txt section 7 (API contracts)
#
# TODO:
#   class ChatRequest(BaseModel): conversation_id: str | None; message: str
#   class ChatResponse(BaseModel): conversation_id, message_id, role,
#       content, tool_calls: list | None
#   class AdminChatResponse(ChatResponse): chart: dict | None
#   class IngestRequest(BaseModel): mode: Literal["full", "incremental"]
#   class IngestResponse(BaseModel): documents_indexed: int; duration_ms: int
