from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
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
