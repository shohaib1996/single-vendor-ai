# Custom uvicorn --loop factory. psycopg's async mode (used by the
# durable LangGraph checkpointer, core/memory.py) does not work under
# Windows' default ProactorEventLoop ("Psycopg cannot use the
# 'ProactorEventLoop' to run in async mode").
#
# uvicorn happens to already select SelectorEventLoop on Windows whenever
# --reload or --workers>1 is used (its use_subprocess flag), which is
# why local dev (always run with --reload) works without this — but
# relying on that as a side effect is fragile: a production run without
# --reload/--workers would silently default back to ProactorEventLoop and
# break. Force SelectorEventLoop unconditionally on Windows instead, via
# `--loop app.core.loop:loop_factory` (see README.md / Dockerfile).
#
# IMPORTANT: uvicorn's `--loop <dotted.path>` mechanism (for anything not
# one of its built-in names "none"/"auto"/"asyncio"/"uvloop") imports
# this object and passes it STRAIGHT to asyncio.run(loop_factory=...) —
# unlike its own built-in factories, there's no extra
# `loop_factory(use_subprocess=...)` indirection call first. This
# function must therefore return an actual event loop INSTANCE directly,
# not a class or another factory — returning the bare class
# (asyncio.SelectorEventLoop instead of asyncio.SelectorEventLoop())
# looks correct but fails opaquely: asyncio.Runner treats the class
# object itself as "the loop", and the first unbound-method call on it
# (e.g. loop.create_task(coro)) raises a confusing
# "BaseEventLoop.create_task() missing 1 required positional argument"
# — coro gets bound to the missing `self`.

import asyncio
import sys


def loop_factory(use_subprocess: bool = False) -> asyncio.AbstractEventLoop:
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()
