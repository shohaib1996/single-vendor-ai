from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents.customer.tools import (
    get_my_orders,
    get_order_detail,
    get_product_details,
    search_products,
)
from app.config import settings
from app.core.memory import close_checkpointer, init_checkpointer
from app.deps.auth import get_current_user
from app.db.store_models import User
from app.routers import chat_admin, chat_customer, health, train


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Opens ONE persistent Postgres connection for the durable LangGraph
    # checkpointer (core/memory.py) and keeps it for the app's lifetime —
    # both agent graphs read app.core.memory.checkpointer at request time.
    # Run uvicorn with --loop app.core.loop:loop_factory (Windows only
    # needs this, but harmless elsewhere) — see core/memory.py's comment
    # for why.
    await init_checkpointer()
    yield
    await close_checkpointer()


app = FastAPI(title="single-vendor-ai", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(train.router, prefix="/api/v1")
app.include_router(chat_customer.router, prefix="/api/v1")
app.include_router(chat_admin.router, prefix="/api/v1")
# TODO (see ai-chatbot-plan.txt section 3/7): also mount app/routers/ingest.py
# once the deprioritized product/category auto-ingestion is built.


# DEBUG routes — test individual tool functions directly, independent of
# the chat endpoints above. Kept (not deleted with /chat-test and
# /admin-chat-test, which were direct stand-ins for chat_customer.py/
# chat_admin.py and are now redundant) since these are still useful for
# isolating a tool-level bug from an agent/prompt-level one.

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
