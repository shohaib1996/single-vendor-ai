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

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from pydantic import BaseModel

from app.agents.customer.graph import build_customer_graph
from app.config import settings
from app.core.rate_limit import check_rate_limit, rate_limit_key
from app.db.store_models import User
from app.deps.auth import get_current_user_optional

router = APIRouter(prefix="/chat", tags=["chat"])

# Tool results from these get surfaced as structured "products" cards in
# the final SSE event instead of relying on the LLM to hand-write
# Markdown links/images for them. gpt-4o-mini could not reliably keep
# product_url vs image_url straight once more than one product was in a
# reply (verified: two separate prompt rewrites, including a worked
# single-item example, still swapped the fields for every item once a
# list of 2-3 products was involved — a text-generation reliability
# ceiling, not a wording problem). Sending the real data structurally and
# letting the frontend render the actual card sidesteps the whole bug
# class rather than continuing to prompt-engineer around it.
PRODUCT_TOOL_NAMES = {"search_products_tool", "get_product_details_tool"}


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _extract_new_products(graph, config: dict, messages_before: int) -> list[dict]:
    """Pulls structured product data out of this turn's tool results only
    (messages_before excludes prior turns' tool calls, which would
    otherwise keep resurfacing old products on every later reply in the
    same conversation)."""
    state = await graph.aget_state(config)
    new_messages = state.values.get("messages", [])[messages_before:]

    products: list[dict] = []
    seen_ids: set[str] = set()
    for msg in new_messages:
        if not (isinstance(msg, ToolMessage) and msg.name in PRODUCT_TOOL_NAMES):
            continue
        try:
            parsed = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            if isinstance(item, dict) and item.get("id") and item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                products.append(item)
    return products


@router.post("/customer")
async def chat_customer(
    body: ChatRequest, request: Request, user: User | None = Depends(get_current_user_optional)
):
    # Checked here, before the StreamingResponse starts — once SSE headers
    # go out with a 200, there's no changing the status code mid-stream.
    check_rate_limit(
        rate_limit_key(request, user.id if user else None),
        settings.RATE_LIMIT_CUSTOMER_PER_MINUTE,
    )

    conversation_id = body.conversation_id or str(uuid.uuid4())
    graph = build_customer_graph(user_id=user.id if user else None)
    config = {"configurable": {"thread_id": conversation_id}}

    async def event_stream() -> AsyncGenerator[str, None]:
        full_content = ""

        prior_state = await graph.aget_state(config)
        messages_before = len(prior_state.values.get("messages", []))

        async for chunk, _metadata in graph.astream(
            {
                "messages": [HumanMessage(content=body.message)],
                "user_id": user.id if user else None,
                "role": user.role if user else None,
            },
            config=config,
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                full_content += chunk.content
                yield _sse({"type": "token", "content": chunk.content})

        products = await _extract_new_products(graph, config, messages_before)

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
                "products": products,
            }
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
