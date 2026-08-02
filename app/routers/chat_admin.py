# POST /api/v1/chat/admin — plan.txt section 6 (Admin analytics chatbot)
# + section 7 (API contract). Replaces the temporary /admin-chat-test
# route in main.py (that route is now removed).
#
# Authorization header REQUIRED, role must be ADMIN (get_current_admin
# re-fetches the live role from Postgres, same as everywhere else).

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from pydantic import BaseModel

from app.agents.admin.graph import build_admin_graph
from app.db.store_models import User
from app.deps.auth import get_current_admin

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/admin")
async def chat_admin(body: ChatRequest, admin: User = Depends(get_current_admin)):
    conversation_id = body.conversation_id or str(uuid.uuid4())
    graph = build_admin_graph()

    async def event_stream() -> AsyncGenerator[str, None]:
        full_content = ""

        async for chunk, _metadata in graph.astream(
            {"messages": [HumanMessage(content=body.message)], "user_id": admin.id},
            config={"configurable": {"thread_id": conversation_id}},
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                full_content += chunk.content
                yield _sse({"type": "token", "content": chunk.content})

        # TODO: "chart" (plan.txt section 6/7 — {type, data} for the
        # Recharts-based admin dashboard) is not implemented — the agent
        # doesn't currently structure any tool result into chart-ready
        # shape, it only returns prose. Needs its own design pass (e.g. a
        # dedicated tool/response_format that returns {type, data}
        # alongside the text), not a small addition to this loop.
        yield _sse(
            {
                "type": "final",
                "conversation_id": conversation_id,
                "message_id": str(uuid.uuid4()),
                "role": "assistant",
                "content": full_content,
                "tool_calls": [],
                "chart": None,
            }
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
