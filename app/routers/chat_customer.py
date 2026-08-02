# POST /api/v1/chat/customer — plan.txt section 5 (Customer chatbot) +
# section 7 (API contract). Replaces the temporary /chat-test route in
# main.py (that route is now removed).
#
# Authorization header is OPTIONAL — guests get product-search + RAG
# tools only; logged-in users additionally get order tools scoped to
# their own user_id (see agents/customer/tools.py build_customer_tools).

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from pydantic import BaseModel

from app.agents.customer.graph import build_customer_graph
from app.db.store_models import User
from app.deps.auth import get_current_user_optional

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/customer")
async def chat_customer(body: ChatRequest, user: User | None = Depends(get_current_user_optional)):
    conversation_id = body.conversation_id or str(uuid.uuid4())
    graph = build_customer_graph(user_id=user.id if user else None)

    async def event_stream() -> AsyncGenerator[str, None]:
        full_content = ""

        async for chunk, _metadata in graph.astream(
            {
                "messages": [HumanMessage(content=body.message)],
                "user_id": user.id if user else None,
                "role": user.role if user else None,
            },
            config={"configurable": {"thread_id": conversation_id}},
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                full_content += chunk.content
                yield _sse({"type": "token", "content": chunk.content})

        # TODO: tool_calls in this final event is always [] — reconstructing
        # it accurately from streamed chunks needs AIMessageChunk
        # accumulation (chunks merge via `+`), not attempted yet. The
        # streamed token content above is already correct/complete;
        # this only affects tool-call metadata in the final payload.
        yield _sse(
            {
                "type": "final",
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4()),
                "role": "assistant",
                "content": full_content,
                "tool_calls": [],
            }
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
