# Async SQLAlchemy engine + session — plan.txt section 3
#
# TODO:
#   - create_async_engine(settings.DATABASE_URL, ...) (asyncpg driver)
#   - async_sessionmaker + get_db() FastAPI dependency (yields AsyncSession)
#   - this connects to the SAME Neon Postgres the Node backend uses
