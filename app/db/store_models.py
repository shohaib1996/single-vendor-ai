# READ-ONLY SQLAlchemy mirrors of the Prisma models this service needs to
# query directly (schema="public" — same tables Prisma owns, this service
# never writes to them or runs migrations against them).
#
# Source of truth for field names/types: single-vendor-backend/prisma/schema.prisma
# Prisma's default table naming is the exact PascalCase model name, hence
# __tablename__ = "User" / "Order" (not "user" / "orders").

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Prisma creates real Postgres enum types for these — mapping the columns
# as plain String works for SELECT (asyncpg returns enum values as text
# automatically) but breaks WHERE-clause comparisons: Postgres refuses to
# compare an enum column to a varchar parameter without an explicit cast
# ("operator does not exist: "OrderStatus" = character varying"). Mapping
# the real enum type here fixes that. create_type=False is required —
# Prisma already owns creating/migrating these types, this service must
# never try to create them.
OrderStatusEnum = PGEnum(
    "PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED",
    name="OrderStatus",
    create_type=False,
)
PaymentStatusEnum = PGEnum(
    "PENDING", "COMPLETED", "FAILED", "REFUNDED",
    name="PaymentStatus",
    create_type=False,
)
RoleEnum = PGEnum(
    "USER", "ADMIN",
    name="Role",
    create_type=False,
)


class User(Base):
    __tablename__ = "User"

    # Deliberately NOT mapping the `password` column (bcrypt hash) — this
    # model should never be able to load it into memory. See
    # ai-chatbot-plan.txt section 10.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(RoleEnum)


class Product(Base):
    __tablename__ = "Product"

    # Minimal columns — just enough to label order items. Extend with
    # more fields (description, images, stock, ...) when building the
    # product search / RAG ingestion tools.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)


class Order(Base):
    __tablename__ = "Order"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    userId: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(OrderStatusEnum)
    total: Mapped[float] = mapped_column(Float)
    createdAt: Mapped[datetime] = mapped_column(DateTime)

    orderItems: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "OrderItem"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    orderId: Mapped[str] = mapped_column(String, ForeignKey("Order.id"))
    productId: Mapped[str] = mapped_column(String, ForeignKey("Product.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)

    order: Mapped["Order"] = relationship(back_populates="orderItems")
    product: Mapped["Product"] = relationship()


class Payment(Base):
    __tablename__ = "Payment"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    orderId: Mapped[str] = mapped_column(String, ForeignKey("Order.id"), unique=True)
    status: Mapped[str] = mapped_column(PaymentStatusEnum)
    method: Mapped[str | None] = mapped_column(String, nullable=True)
    paidAt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="payment")


# TODO — add as tools need them:
#   class Category(Base):    __tablename__ = "Category"
#   class Brand(Base):       __tablename__ = "Brand"
#   class ProductSpecification(Base): __tablename__ = "ProductSpecification"
#   class ProductQuestion(Base):      __tablename__ = "ProductQuestion"
#   class ProductAnswer(Base):        __tablename__ = "ProductAnswer"
#   class Review(Base):      __tablename__ = "Review"
