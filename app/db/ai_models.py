# This service's OWN tables — schema "ai_chat" (AiBase, separate from the
# read-only Prisma mirrors in store_models.py — see session.py). Created
# via scripts/init_ai_schema.py, not Prisma's migrations.

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import AiBase


class TrainingDocument(AiBase):
    """One admin-submitted 'Train Bot' entry (plan.txt section 4 update) —
    either pasted text or an uploaded policy document. chunk_ids records
    the exact Pinecone vector ids produced at ingestion time, so deleting
    this row can delete precisely those vectors (Pinecone serverless
    indexes don't support delete-by-metadata-filter reliably, only
    delete-by-id — see app/rag/ingest.py)."""

    __tablename__ = "training_documents"
    __table_args__ = {"schema": "ai_chat"}

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String)  # "text" | "file"
    original_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# TODO — future, per plan.txt section 5 (conversation memory) once ready
# to move off the in-process MemorySaver checkpointer:
#   class Conversation(AiBase): __tablename__ = "conversations"; __table_args__ = {"schema": "ai_chat"}
#   class Message(AiBase):      __tablename__ = "messages"; __table_args__ = {"schema": "ai_chat"}
