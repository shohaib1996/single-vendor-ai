# Durable LangGraph checkpointer — plan.txt section 5/6/12. Replaces the
# in-process MemorySaver both agent graphs used until now.
#
# Two real gotchas hit getting this working (Windows + Neon specific):
#
#   1. psycopg's async mode does not work under Windows' default
#      ProactorEventLoop ("Psycopg cannot use the 'ProactorEventLoop' to
#      run in async mode"). Run uvicorn with
#      `--loop app.core.loop:loop_factory` (see core/loop.py) to force
#      SelectorEventLoop on Windows. asyncpg (used everywhere else in
#      this service) works fine under SelectorEventLoop too — verified,
#      not just assumed.
#
#   2. Neon's pooled endpoint (hostname with "-pooler.") REJECTS the
#      `options` startup parameter outright ("unsupported startup
#      parameter in options: search_path... Please use unpooled
#      connection"), which is how a non-default Postgres schema gets
#      selected for a plain psycopg connection string. A runtime `SET
#      search_path` after connecting would have the same underlying
#      problem under PgBouncer transaction pooling (not guaranteed to
#      survive across transactions on pooled connections) even if Neon
#      didn't reject it outright. Fix: use Neon's DIRECT/unpooled
#      endpoint for this connection (strip "-pooler" from the hostname)
#      — appropriate here anyway, since the checkpointer holds one
#      long-lived connection rather than many short pooled ones.

from urllib.parse import quote

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings


def get_checkpointer_dsn() -> str:
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    dsn = dsn.replace("ssl=require", "sslmode=require")
    dsn = dsn.replace("-pooler.", ".", 1)
    options = quote("-c search_path=ai_chat", safe="")
    sep = "&" if "?" in dsn else "?"
    return f"{dsn}{sep}options={options}"


def get_checkpointer_cm():
    return AsyncPostgresSaver.from_conn_string(get_checkpointer_dsn())


# Module-level shared instance — opened once at app startup (main.py's
# lifespan), reused by every request. Re-opening per-request would open/
# close a Postgres connection on every single chat message. Graph builder
# functions (agents/customer/graph.py, agents/admin/graph.py) read this
# via `import app.core.memory as memory; memory.checkpointer` at CALL
# time, not `from app.core.memory import checkpointer` at import time —
# the latter would freeze in the pre-startup None value forever, since
# Python import binds a reference to the value at that instant.
_checkpointer_cm = None
checkpointer: AsyncPostgresSaver | None = None


async def init_checkpointer() -> None:
    global _checkpointer_cm, checkpointer
    _checkpointer_cm = get_checkpointer_cm()
    checkpointer = await _checkpointer_cm.__aenter__()
    await checkpointer.setup()


async def close_checkpointer() -> None:
    global _checkpointer_cm, checkpointer
    if _checkpointer_cm is not None:
        await _checkpointer_cm.__aexit__(None, None, None)
        _checkpointer_cm = None
        checkpointer = None
