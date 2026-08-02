# Customer agent tools — plan.txt section 5.
#
# SECURITY: every function here takes `user_id` as an explicit argument
# that must come from the verified JWT (app.deps.auth), never from chat
# text or an LLM-generated argument. When these get wired into the actual
# LangGraph tool nodes (graph.py), bind user_id via a closure/partial at
# request time — do NOT expose it as an LLM-fillable tool parameter, or
# the model could be persuaded to look up someone else's orders. This is
# also why these query the DB directly instead of the backend's
# GET /orders/:id, which has no ownership check at all today (plan.txt
# section 1 / section 10).

import httpx
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.session import async_session
from app.db.store_models import Order, OrderItem


async def get_my_orders(user_id: str, status: str | None = None) -> list[dict]:
    """List the calling user's own orders, optionally filtered by status.

    Also fixes a gap in the existing Node REST API: GET /api/v1/orders
    has no server-side `status` filter today (see plan.txt section 1) —
    this implements it properly.
    """
    async with async_session() as db:
        stmt = select(Order).where(Order.userId == user_id).order_by(Order.createdAt.desc())
        if status:
            stmt = stmt.where(Order.status == status)
        result = await db.execute(stmt)
        orders = result.scalars().all()
        return [_serialize_order(o) for o in orders]


async def get_order_detail(user_id: str, order_id: str) -> dict | None:
    """Look up a single order, scoped to the caller.

    WHERE id = order_id AND userId = user_id — if the order doesn't
    belong to the caller, returns None (never another user's order),
    unlike the backend's GET /orders/:id which has no such check.
    """
    async with async_session() as db:
        stmt = (
            select(Order)
            .where(Order.id == order_id, Order.userId == user_id)
            .options(
                selectinload(Order.orderItems).selectinload(OrderItem.product),
                selectinload(Order.payment),
            )
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        return _serialize_order(order, include_items=True) if order else None


def _serialize_order(order: Order, include_items: bool = False) -> dict:
    data: dict = {
        "id": order.id,
        "status": order.status,
        "total": order.total,
        "createdAt": order.createdAt.isoformat(),
    }
    if include_items:
        data["items"] = [
            {"product": item.product.name, "quantity": item.quantity, "price": item.price}
            for item in order.orderItems
        ]
        if order.payment:
            data["payment"] = {"status": order.payment.status, "method": order.payment.method}
    return data


# search_products / get_product_details wrap the Node backend's PUBLIC
# /products endpoints (no auth needed) instead of re-implementing its
# filter logic — categoryId descendant-resolution, brand-name matching,
# spec-based filters, etc. (see plan.txt section 1). No ownership scoping
# needed here since this data isn't user-specific.

async def search_products(
    query: str | None = None,
    category_id: str | None = None,
    brand: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search the public product catalog.

    category_id must be an actual Category id (not a name) — there's no
    name->id resolution tool yet, so the agent should only pass this when
    it already has an id (e.g. from a prior search result).
    """
    params = {
        "searchTerm": query,
        "categoryId": category_id,
        "brand": brand,
        "priceRangeMin": price_min,
        "priceRangeMax": price_max,
        "limit": limit,
    }
    params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient(base_url=settings.NODE_API_BASE_URL, timeout=10) as client:
        response = await client.get("/products", params=params)
        response.raise_for_status()
        payload = response.json()

    return [_serialize_product_summary(p) for p in payload.get("data", [])]


async def get_product_details(product_id: str) -> dict | None:
    """Full detail for a single product (specs, category, brand)."""
    async with httpx.AsyncClient(base_url=settings.NODE_API_BASE_URL, timeout=10) as client:
        response = await client.get(f"/products/{product_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()

    return _serialize_product_detail(payload.get("data"))


def _serialize_product_summary(product: dict) -> dict:
    return {
        "id": product.get("id"),
        "name": product.get("name"),
        "price": product.get("price"),
        "discountedPrice": product.get("discountedPrice") if product.get("isDiscountActive") else None,
        "stock": product.get("stock"),
        "category": (product.get("category") or {}).get("name"),
        "brand": (product.get("brand") or {}).get("name"),
    }


def _serialize_product_detail(product: dict | None) -> dict | None:
    if product is None:
        return None
    return {
        **_serialize_product_summary(product),
        "description": product.get("description"),
        "specifications": [
            {"key": s.get("key"), "value": s.get("value")}
            for s in product.get("specifications", [])
        ],
    }


# --- LangChain tool wrappers, built fresh per request (graph.py) -----------
#
# user_id is bound here via closure — it is NEVER an LLM-fillable
# parameter on get_my_orders_tool/get_order_detail_tool. This is the
# actual enforcement point for the security note at the top of this file.
# For a guest (user_id is None), order tools are omitted from the list
# entirely rather than included and made to fail — a smaller, safer tool
# surface for the model to reason over.

def build_customer_tools(user_id: str | None) -> list:
    tools = []

    if user_id:

        @tool
        async def get_my_orders_tool(status: str | None = None) -> list[dict]:
            """List the current user's own orders. Optionally filter by
            status: one of PENDING, PAID, SHIPPED, DELIVERED, CANCELLED."""
            return await get_my_orders(user_id=user_id, status=status)

        @tool
        async def get_order_detail_tool(order_id: str) -> dict:
            """Get full detail (items, quantities, prices, payment status)
            for one of the current user's own orders, by its order id."""
            result = await get_order_detail(user_id=user_id, order_id=order_id)
            return result or {"error": "Order not found"}

        tools += [get_my_orders_tool, get_order_detail_tool]

    @tool
    async def search_products_tool(
        query: str | None = None,
        brand: str | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
    ) -> list[dict]:
        """Search the store's product catalog by keyword, brand, and/or
        price range. Returns a short summary (name, price, stock,
        category, brand) for each match."""
        return await search_products(query=query, brand=brand, price_min=price_min, price_max=price_max)

    @tool
    async def get_product_details_tool(product_id: str) -> dict:
        """Get full details (description, specifications, stock) for one
        product by its product id — use after search_products_tool to
        look closer at a specific result."""
        result = await get_product_details(product_id)
        return result or {"error": "Product not found"}

    tools += [search_products_tool, get_product_details_tool]

    return tools


# TODO:
#   def rag_search(query: str) -> list[dict]
#       app.rag.retriever similarity search over kb_documents/product/QnA
#       (add to build_customer_tools once the RAG pipeline exists)
