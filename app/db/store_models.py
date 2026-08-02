# READ-ONLY SQLAlchemy mirrors of the Prisma models this service needs to
# query directly (schema="public" — same tables Prisma owns, this service
# never writes to them or runs migrations against them).
#
# Source of truth for field names/types: single-vendor-backend/prisma/schema.prisma
# Prisma's default table naming is the exact PascalCase model name, hence
# __tablename__ = "User" (not "user" / "users").

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "User"

    # Deliberately NOT mapping the `password` column (bcrypt hash) — this
    # model should never be able to load it into memory. See
    # ai-chatbot-plan.txt section 10.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)  # "USER" | "ADMIN"


# TODO — add as tools need them:
#   class Order(Base):       __tablename__ = "Order"
#   class OrderItem(Base):   __tablename__ = "OrderItem"
#   class Payment(Base):     __tablename__ = "Payment"
#   class Product(Base):     __tablename__ = "Product"
#   class Category(Base):    __tablename__ = "Category"
#   class Brand(Base):       __tablename__ = "Brand"
#   class ProductSpecification(Base): __tablename__ = "ProductSpecification"
#   class ProductQuestion(Base):      __tablename__ = "ProductQuestion"
#   class ProductAnswer(Base):        __tablename__ = "ProductAnswer"
#   class Review(Base):      __tablename__ = "Review"
