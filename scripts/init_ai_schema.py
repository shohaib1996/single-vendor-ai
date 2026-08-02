# One-time (and safe to re-run) setup: creates the `ai_chat` Postgres
# schema and this service's own tables. Deliberately NOT Alembic yet —
# there's a single table and no migration history to manage. Move to
# Alembic (already in requirements.txt) once real schema changes need
# versioning across environments.
#
# Run with: uv run python -m scripts.init_ai_schema

import asyncio

from sqlalchemy import text

from app.db import ai_models  # noqa: F401 — registers TrainingDocument on AiBase.metadata
from app.db.session import AiBase, engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai_chat"))
        await conn.run_sync(AiBase.metadata.create_all)
    print("ai_chat schema + tables ready.")


if __name__ == "__main__":
    asyncio.run(main())
