from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.deps.auth import get_current_user
from app.db.store_models import User
from app.routers import health

# TODO (see ai-chatbot-plan.txt section 3): once built, also mount:
#   from app.routers import chat_customer, chat_admin, ingest
#   app.include_router(chat_customer.router, prefix="/api/v1")
#   app.include_router(chat_admin.router, prefix="/api/v1")
#   app.include_router(ingest.router, prefix="/api/v1")

app = FastAPI(title="single-vendor-ai")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


# TEMPORARY — checkpoint 2 from ai-chatbot-plan.txt: proves this service
# can independently verify a JWT issued by the Node backend and re-fetch
# the live user row from the shared DB. Delete once chat_customer.py is
# wired up for real (get_current_user will be used there instead).
@app.get("/whoami")
async def whoami(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
