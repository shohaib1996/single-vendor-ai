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
from app.rag.vectorstore import get_vectorstore


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

def _flatten_categories(categories: list[dict]) -> list[dict]:
    """Recurses to whatever depth the category tree actually has — the
    /categories response only nests one level today (e.g. Laptop >
    Gaming/Business/Budget), but this must not assume that stays true."""
    flat: list[dict] = []
    for cat in categories:
        flat.append(cat)
        flat.extend(_flatten_categories(cat.get("children", [])))
    return flat


async def _resolve_category_id(query: str) -> str | None:
    """The Node backend's product search ONLY does a substring match on
    name/description — it never considers category. A real product named
    "Bose QuietComfort Ultra" has no way to match a search for
    "headphone" even though its category IS Headphone > Wired, so a
    plain searchTerm query silently returns zero results (confirmed —
    this is what a real user hit). Resolve category-shaped query terms
    to a real categoryId first so search_products can use the backend's
    recursive categoryId filter instead of a text match doomed to miss.

    Not cached — the category tree is small and rarely changes, but this
    adds one extra request per search_products call. Fine at this scale;
    add a TTL cache here first if this ever shows up as a bottleneck.
    """
    async with httpx.AsyncClient(base_url=settings.NODE_API_BASE_URL, timeout=10) as client:
        response = await client.get("/categories")
        response.raise_for_status()
        categories = response.json().get("data", [])

    flat = _flatten_categories(categories)

    query_lower = query.lower()
    matches = [c for c in flat if c["name"].lower() in query_lower]
    if not matches:
        return None

    # Prefer the most specific match. Name length alone isn't enough —
    # "gaming laptop" matches BOTH "Laptop" (parent) and "Gaming" (child)
    # and they're the same length, so a pure longest-name tiebreak picked
    # the parent arbitrarily (confirmed: returned Business+Budget+Gaming
    # laptops mixed together instead of just Gaming). Prefer any match
    # that has a parent (i.e. is not top-level) before falling back to
    # top-level matches, THEN break remaining ties by name length.
    child_matches = [c for c in matches if c.get("parentId")]
    candidates = child_matches or matches
    return max(candidates, key=lambda c: len(c["name"]))["id"]


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
    search_term = query

    if query and category_id is None:
        resolved = await _resolve_category_id(query)
        if resolved:
            # Use the resolved category filter INSTEAD of the raw text
            # search — the backend ANDs searchTerm with categoryId, and
            # the query text (e.g. "headphone") usually won't appear in
            # the matching products' name/description, so keeping it
            # would zero out the very results the category match found.
            category_id = resolved
            search_term = None

    params = {
        "searchTerm": search_term,
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
    images = product.get("images") or []
    return {
        "id": product.get("id"),
        "name": product.get("name"),
        "price": product.get("price"),
        "discountedPrice": product.get("discountedPrice") if product.get("isDiscountActive") else None,
        "stock": product.get("stock"),
        "category": (product.get("category") or {}).get("name"),
        "brand": (product.get("brand") or {}).get("name"),
        # Relative path — resolves against whatever origin the storefront
        # is actually served from (dev or prod), no frontend base URL
        # needs configuring here. Distinctly-named from image_url on
        # purpose — gpt-4o-mini confused a generic "url"/"image" pair,
        # swapping which one it put in the Markdown link vs image tag
        # (verified: it linked the product name to the image file and
        # dropped the page link entirely). Explicit names fixed it.
        "product_url": f"/products/{product.get('id')}",
        "image_url": images[0] if images else None,
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


async def rag_search(query: str, k: int = 4) -> list[dict]:
    """Semantic search over admin-trained knowledge (policies, FAQs, etc
    submitted via the "Train Bot" admin feature — plan.txt section 4).
    Not user-specific, so no ownership scoping needed."""
    vectorstore = get_vectorstore()
    docs = await vectorstore.asimilarity_search(query, k=k)
    return [{"title": d.metadata.get("title"), "content": d.page_content} for d in docs]


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

    @tool
    async def rag_search_tool(query: str) -> list[dict]:
        """Search the store's policy/knowledge base — return policy,
        shipping, how order placing works, warranty, etc. Use this for
        any question that isn't about a specific order or product."""
        return await rag_search(query)

    tools += [search_products_tool, get_product_details_tool, rag_search_tool]

    return tools
