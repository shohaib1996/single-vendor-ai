# READ-ONLY SQLAlchemy mirrors of the Prisma models this service needs to
# query directly (schema="public" — same tables Prisma owns, this service
# never writes to them or runs migrations against them).
#
# Source of truth for field names/types: single-vendor-backend/prisma/schema.prisma
#
# TODO — model only what tools actually need, e.g.:
#   class User(Base):        __tablename__ = "User"
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
#
# Note: Prisma's default table naming is the PascalCase model name (as
# above), not snake_case — verify against the actual DB with \dt in psql
# before assuming.
