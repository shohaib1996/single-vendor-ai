from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


# statement_cache_size=0 disables asyncpg's prepared-statement cache, which
# is required against Neon's pooled (pgbouncer) endpoint — see
# ai-chatbot-plan.txt section 3 / the -pooler hostname note.
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"statement_cache_size": 0},
)

async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
