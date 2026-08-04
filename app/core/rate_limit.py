# Rate limiting for the chat endpoints — plan.txt section 10 ("Rate-limit
# both chat endpoints per user — LLM calls cost money and are an abuse
# vector"). This was the single highest-priority open gap: nothing stood
# between a request loop (or a bug, or a bored visitor) and unlimited
# real OpenAI spend.
#
# In-process, in-memory sliding window — NOT Redis. This service runs as
# one local `uvicorn` process right now; Redis would be a second piece of
# infrastructure to install/run for no real benefit at this scale. If this
# is ever deployed with multiple workers, swap _buckets for Redis
# (INCR + EXPIRE) — check_rate_limit()'s signature stays the same either
# way, callers don't need to change.

import time
from collections import defaultdict

from fastapi import HTTPException, Request

_buckets: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str, max_requests: int, window_seconds: int = 60) -> None:
    """Raises 429 if `key` has made >= max_requests in the last
    window_seconds. Call this AFTER auth is resolved (so the key can be
    the real user id, not just an IP) but BEFORE doing any LLM work."""
    now = time.monotonic()
    window_start = now - window_seconds
    timestamps = _buckets[key]

    while timestamps and timestamps[0] < window_start:
        timestamps.pop(0)

    if len(timestamps) >= max_requests:
        retry_after = max(1, int(window_seconds - (now - timestamps[0])) + 1)
        raise HTTPException(
            status_code=429,
            detail="Too many messages — please wait a moment before sending another.",
            headers={"Retry-After": str(retry_after)},
        )

    timestamps.append(now)


def rate_limit_key(request: Request, user_id: str | None) -> str:
    """Prefer the real user id (survives IP changes, and is what
    actually identifies who's spending the money) — fall back to IP only
    for guests, who have no other identity on the customer chat endpoint."""
    if user_id:
        return f"user:{user_id}"
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"
