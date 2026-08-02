from langchain_core.messages import HumanMessage

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agents.customer.graph import build_customer_graph
from app.agents.customer.tools import (
    get_my_orders,
    get_order_detail,
    get_product_details,
    search_products,
)
from app.config import settings
from app.deps.auth import get_current_user, get_current_user_optional
from app.db.store_models import User
from app.routers import health, train

# TODO (see ai-chatbot-plan.txt section 3): once built, also mount:
#   from app.routers import chat_customer, chat_admin, ingest
#   app.include_router(chat_customer.router, prefix="/api/v1")
#   app.include_router(chat_admin.router, prefix="/api/v1")
#   app.include_router(ingest.router, prefix="/api/v1")

app = FastAPI(title="single-vendor-ai")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(train.router, prefix="/api/v1")


# TEMPORARY test routes — delete once chat_customer.py + the real LangGraph
# agent are wired up (these tool functions will be called from inside the
# graph instead, with user_id bound from state, not a route param).

@app.get("/whoami")
async def whoami(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@app.get("/my-orders")
async def my_orders(status: str | None = None, user: User = Depends(get_current_user)):
    return await get_my_orders(user_id=user.id, status=status)


@app.get("/my-orders/{order_id}")
async def my_order_detail(order_id: str, user: User = Depends(get_current_user)):
    order = await get_order_detail(user_id=user.id, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# No auth on these two — mirrors the Node backend's public /products routes.

@app.get("/search-products")
async def search_products_route(
    query: str | None = None,
    category_id: str | None = None,
    brand: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
):
    return await search_products(
        query=query,
        category_id=category_id,
        brand=brand,
        price_min=price_min,
        price_max=price_max,
    )


@app.get("/product-detail/{product_id}")
async def product_detail_route(product_id: str):
    product = await get_product_details(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# TEMPORARY: synchronous, non-streaming stand-in for the real
# POST /api/v1/chat/customer SSE endpoint (plan.txt section 7), just to
# prove the LangGraph agent's tool-calling loop works end to end. Works
# for both guests (no Authorization header) and logged-in users.

class ChatTestBody(BaseModel):
    message: str
    conversation_id: str = "test-thread"


@app.post("/chat-test")
async def chat_test(body: ChatTestBody, user: User | None = Depends(get_current_user_optional)):
    graph = build_customer_graph(user_id=user.id if user else None)
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=body.message)],
            "user_id": user.id if user else None,
            "role": user.role if user else None,
        },
        config={"configurable": {"thread_id": body.conversation_id}},
    )
    return {"reply": result["messages"][-1].content}
