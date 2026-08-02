# Admin analytics agent tools — plan.txt section 6. All read-only, hit
# Postgres directly. Deliberately NOT reusing the existing
# GET /dashboard/analytics endpoint's buggy exact-timestamp groupBy —
# these use proper DATE_TRUNC day/week/month bucketing (plan.txt
# section 1's noted bug).
#
# No ownership scoping needed (unlike the customer tools) — this whole
# agent is admin-only, gated by get_current_admin before the graph ever
# runs (see routers/chat_admin.py, not built yet).

from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool
from sqlalchemy import func, select

from app.db.session import async_session
from app.db.store_models import (
    Category,
    Order,
    OrderItem,
    Product,
    ProductAnswer,
    ProductQuestion,
    User,
)

_VALID_GRANULARITY = {"day", "week", "month"}


def _bucket(column, granularity: str):
    if granularity not in _VALID_GRANULARITY:
        raise ValueError(f"granularity must be one of {_VALID_GRANULARITY}")
    return func.date_trunc(granularity, column)


def _parse_date(value: str) -> datetime:
    """Order/User.createdAt are TIMESTAMP WITHOUT TIME ZONE — asyncpg will
    NOT implicitly cast a plain string bind parameter to timestamp
    ("operator does not exist: timestamp without time zone >= character
    varying"), so date_from/date_to args (naturally ISO date strings from
    an LLM tool call) must be parsed to datetime before use in a query."""
    return datetime.fromisoformat(value).replace(tzinfo=None)


async def get_analytics_summary() -> dict:
    """Same KPI set as the existing admin dashboard — current snapshot
    numbers, no date range."""
    async with async_session() as db:
        total_revenue = await db.scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(Order.status == "DELIVERED")
        )
        total_orders = await db.scalar(select(func.count()).select_from(Order))
        total_customers = await db.scalar(
            select(func.count()).select_from(User).where(User.role == "USER")
        )
        total_products = await db.scalar(select(func.count()).select_from(Product))
        pending_orders = await db.scalar(
            select(func.count()).select_from(Order).where(Order.status == "PENDING")
        )
        out_of_stock = await db.scalar(
            select(func.count()).select_from(Product).where(Product.stock == 0)
        )
        # Order/User.createdAt are Postgres TIMESTAMP WITHOUT TIME ZONE
        # (Prisma's DateTime default) — asyncpg refuses to bind a
        # tz-aware Python datetime against that column type, so strip
        # tzinfo after computing in UTC.
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).replace(tzinfo=None)
        new_customers = await db.scalar(
            select(func.count()).select_from(User).where(User.createdAt >= thirty_days_ago)
        )
        unanswered_questions = await db.scalar(
            select(func.count())
            .select_from(ProductQuestion)
            .outerjoin(ProductAnswer, ProductAnswer.questionId == ProductQuestion.id)
            .where(ProductAnswer.id.is_(None))
        )

        return {
            "totalRevenue": total_revenue,
            "totalOrders": total_orders,
            "totalCustomers": total_customers,
            "totalProducts": total_products,
            "pendingOrders": pending_orders,
            "outOfStock": out_of_stock,
            "newCustomers": new_customers,
            "unansweredQuestions": unanswered_questions,
        }


async def sales_over_range(date_from: str, date_to: str, granularity: str = "day") -> list[dict]:
    """Revenue trend bucketed by day/week/month between two ISO dates.
    Fixes the existing dashboard's bug of grouping by exact timestamp."""
    async with async_session() as db:
        bucket = _bucket(Order.createdAt, granularity).label("bucket")
        stmt = (
            select(bucket, func.sum(Order.total).label("revenue"), func.count().label("order_count"))
            .where(Order.createdAt >= _parse_date(date_from), Order.createdAt < _parse_date(date_to))
            .group_by(bucket)
            .order_by(bucket)
        )
        result = await db.execute(stmt)
        return [
            {"period": row.bucket.isoformat(), "revenue": row.revenue, "orders": row.order_count}
            for row in result
        ]


async def top_products(limit: int = 5, date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    """Top-selling products by quantity sold, optionally within a date range."""
    async with async_session() as db:
        stmt = (
            select(
                Product.id,
                Product.name,
                func.sum(OrderItem.quantity).label("total_quantity"),
            )
            .join(OrderItem, OrderItem.productId == Product.id)
            .join(Order, Order.id == OrderItem.orderId)
        )
        if date_from:
            stmt = stmt.where(Order.createdAt >= _parse_date(date_from))
        if date_to:
            stmt = stmt.where(Order.createdAt < _parse_date(date_to))
        stmt = stmt.group_by(Product.id, Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(limit)

        result = await db.execute(stmt)
        return [{"productId": r.id, "name": r.name, "quantitySold": r.total_quantity} for r in result]


async def top_categories(limit: int = 5, date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    """Top categories by total sales revenue, optionally within a date range."""
    async with async_session() as db:
        stmt = (
            select(
                Category.id,
                Category.name,
                func.sum(OrderItem.price * OrderItem.quantity).label("total_sales"),
            )
            .join(Product, Product.categoryId == Category.id)
            .join(OrderItem, OrderItem.productId == Product.id)
            .join(Order, Order.id == OrderItem.orderId)
        )
        if date_from:
            stmt = stmt.where(Order.createdAt >= _parse_date(date_from))
        if date_to:
            stmt = stmt.where(Order.createdAt < _parse_date(date_to))
        stmt = (
            stmt.group_by(Category.id, Category.name)
            .order_by(func.sum(OrderItem.price * OrderItem.quantity).desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        return [{"categoryId": r.id, "name": r.name, "totalSales": r.total_sales} for r in result]


async def low_stock_products(threshold: int = 5) -> list[dict]:
    """Products at or below a stock threshold."""
    async with async_session() as db:
        stmt = (
            select(Product.id, Product.name, Product.stock)
            .where(Product.stock <= threshold)
            .order_by(Product.stock)
        )
        result = await db.execute(stmt)
        return [{"productId": r.id, "name": r.name, "stock": r.stock} for r in result]


async def pending_orders(limit: int = 10) -> list[dict]:
    """Most recent pending orders, with the customer's email."""
    async with async_session() as db:
        stmt = (
            select(Order.id, Order.total, Order.createdAt, User.email)
            .join(User, User.id == Order.userId)
            .where(Order.status == "PENDING")
            .order_by(Order.createdAt.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [
            {"orderId": r.id, "total": r.total, "createdAt": r.createdAt.isoformat(), "customerEmail": r.email}
            for r in result
        ]


async def customer_growth(date_from: str, date_to: str, granularity: str = "day") -> list[dict]:
    """New customer signups bucketed by day/week/month between two ISO dates."""
    async with async_session() as db:
        bucket = _bucket(User.createdAt, granularity).label("bucket")
        stmt = (
            select(bucket, func.count().label("new_customers"))
            .where(User.createdAt >= _parse_date(date_from), User.createdAt < _parse_date(date_to), User.role == "USER")
            .group_by(bucket)
            .order_by(bucket)
        )
        result = await db.execute(stmt)
        return [{"period": row.bucket.isoformat(), "newCustomers": row.new_customers} for row in result]


async def unanswered_questions(limit: int = 10) -> list[dict]:
    """Product questions from customers that haven't been answered yet."""
    async with async_session() as db:
        stmt = (
            select(ProductQuestion.id, ProductQuestion.question, ProductQuestion.createdAt, Product.name)
            .join(Product, Product.id == ProductQuestion.productId)
            .outerjoin(ProductAnswer, ProductAnswer.questionId == ProductQuestion.id)
            .where(ProductAnswer.id.is_(None))
            .order_by(ProductQuestion.createdAt.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [
            {"questionId": r.id, "question": r.question, "product": r.name, "createdAt": r.createdAt.isoformat()}
            for r in result
        ]


# --- LangChain tool wrappers ------------------------------------------------
#
# Unlike the customer tools, no per-request closure binding is needed —
# this whole agent is gated admin-only at the route level (routers/
# chat_admin.py, not built yet), and none of these queries are scoped to
# a particular user. build_admin_tools() still returns a fresh list per
# call for consistency with build_customer_tools()'s shape.

def build_admin_tools() -> list:
    @tool
    async def get_analytics_summary_tool() -> dict:
        """The TOTAL/EXACT counts for: revenue, orders, customers,
        products, pending orders, out-of-stock products, new customers
        (last 30 days), unanswered questions. Use this — not
        pending_orders_tool or unanswered_questions_tool — for any "how
        many" question, since those two only return a short preview
        list, not a total count."""
        return await get_analytics_summary()

    @tool
    async def sales_over_range_tool(date_from: str, date_to: str, granularity: str = "day") -> list[dict]:
        """Revenue trend between two ISO dates (e.g. "2026-01-01"),
        bucketed by "day", "week", or "month"."""
        return await sales_over_range(date_from, date_to, granularity)

    @tool
    async def top_products_tool(
        limit: int = 5, date_from: str | None = None, date_to: str | None = None
    ) -> list[dict]:
        """Best-selling products by quantity sold, optionally within an
        ISO date range."""
        return await top_products(limit, date_from, date_to)

    @tool
    async def top_categories_tool(
        limit: int = 5, date_from: str | None = None, date_to: str | None = None
    ) -> list[dict]:
        """Top categories by total sales revenue, optionally within an
        ISO date range."""
        return await top_categories(limit, date_from, date_to)

    @tool
    async def low_stock_products_tool(threshold: int = 5) -> list[dict]:
        """Products at or below a given stock threshold."""
        return await low_stock_products(threshold)

    @tool
    async def pending_orders_tool(limit: int = 10) -> list[dict]:
        """Lists only the `limit` MOST RECENT orders in PENDING status
        (default 10), with customer email — this is a preview list, NOT
        the total count. For "how many pending orders" style questions,
        use get_analytics_summary_tool instead, which has the real total."""
        return await pending_orders(limit)

    @tool
    async def customer_growth_tool(date_from: str, date_to: str, granularity: str = "day") -> list[dict]:
        """New customer signups between two ISO dates, bucketed by
        "day", "week", or "month"."""
        return await customer_growth(date_from, date_to, granularity)

    @tool
    async def unanswered_questions_tool(limit: int = 10) -> list[dict]:
        """Lists only the `limit` MOST RECENT unanswered product
        questions (default 10) — this is a preview list, NOT the total
        count. For "how many unanswered questions" style questions, use
        get_analytics_summary_tool instead, which has the real total."""
        return await unanswered_questions(limit)

    return [
        get_analytics_summary_tool,
        sales_over_range_tool,
        top_products_tool,
        top_categories_tool,
        low_stock_products_tool,
        pending_orders_tool,
        customer_growth_tool,
        unanswered_questions_tool,
    ]
