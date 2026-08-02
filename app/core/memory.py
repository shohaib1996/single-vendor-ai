# Durable LangGraph checkpointer — plan.txt section 5/6/12. Replaces the
# in-process MemorySaver both agent graphs used until now.
#
# Three real gotchas hit getting this working (Windows + Neon specific):
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
#      endpoint for this connection (strip "-pooler" from the hostname).
#
#   3. A SINGLE long-lived psycopg connection (AsyncPostgresSaver.
#      from_conn_string(), which wraps one bare AsyncConnection) goes
#      silently stale after Neon drops it for being idle — confirmed:
#      the server sat idle for ~10 minutes during unrelated debugging,
#      and the next chat request failed with a 200 status but a
#      zero-byte, incomplete streamed body (curl: "transfer closed with
#      outstanding read data remaining" / ERR_INCOMPLETE_CHUNKED_ENCODING
#      in a browser) — no exception surfaced anywhere obvious, it just
#      silently produced a broken response. A fresh ad-hoc connection
#      worked fine immediately after, proving the graph/LLM/checkpointer
#      logic itself was never the problem. Fix: use a psycopg_pool.
#      AsyncConnectionPool instead of a bare connection —
#      AsyncPostgresSaver accepts either (see _ainternal.Conn) — the pool
#      health-checks and transparently replaces dead connections instead
#      of silently trying to use one.

from urllib.parse import quote

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings


def get_checkpointer_dsn() -> str:
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    dsn = dsn.replace("ssl=require", "sslmode=require")
    dsn = dsn.replace("-pooler.", ".", 1)
    options = quote("-c search_path=ai_chat", safe="")
    sep = "&" if "?" in dsn else "?"
    return f"{dsn}{sep}options={options}"


# Module-level shared instances — opened once at app startup (main.py's
# lifespan), reused by every request. Graph builder functions
# (agents/customer/graph.py, agents/admin/graph.py) read `checkpointer`
# via `import app.core.memory as memory; memory.checkpointer` at CALL
# time, not `from app.core.memory import checkpointer` at import time —
# the latter would freeze in the pre-startup None value forever, since
# Python import binds a reference to the value at that instant.
_pool: AsyncConnectionPool | None = None
checkpointer: AsyncPostgresSaver | None = None


async def init_checkpointer() -> None:
    global _pool, checkpointer
    _pool = AsyncConnectionPool(
        conninfo=get_checkpointer_dsn(),
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    await _pool.open()
    checkpointer = AsyncPostgresSaver(_pool)
    await checkpointer.setup()


async def close_checkpointer() -> None:
    global _pool, checkpointer
    if _pool is not None:
        await _pool.close()
        _pool = None
        checkpointer = None
