# JWT auth dependencies — plan.txt section 2b + section 10 (security)
#
# Mirrors single-vendor-backend/src/app/middleware/auth.ts exactly:
#   - token from `Authorization: Bearer <token>` header only (no cookies)
#   - jwt.decode with the same HS256 JWT_SECRET
#   - payload is {id, email, role, iat, exp} — do NOT trust `role` alone,
#     re-fetch the User row from Postgres by id to get the CURRENT role,
#     same as the Node middleware does

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.db.store_models import User


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user
