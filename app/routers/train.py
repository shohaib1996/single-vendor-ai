# "Train Bot" admin endpoints — plan.txt section 4 update. Admin-only
# (get_current_admin re-fetches the live role from Postgres, same as
# everywhere else in this service). This is the backend half of the
# planned Next.js admin panel "Train Bot" page (frontend not built yet —
# see plan.txt Phase 4).

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.ai_models import TrainingDocument
from app.db.session import get_db
from app.db.store_models import User
from app.deps.auth import get_current_admin
from app.rag.ingest import delete_document, ingest_text
from app.rag.loaders import extract_text_from_upload

router = APIRouter(prefix="/train", tags=["train"])


class TrainTextBody(BaseModel):
    title: str
    content: str


@router.post("/text")
async def train_from_text(
    body: TrainTextBody,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    doc_id = str(uuid.uuid4())
    chunk_ids = await ingest_text(doc_id, body.title, body.content)

    doc = TrainingDocument(
        id=doc_id,
        title=body.title,
        source_type="text",
        content=body.content,
        chunk_ids=chunk_ids,
        chunk_count=len(chunk_ids),
    )
    db.add(doc)
    await db.commit()

    return {"id": doc_id, "chunks_indexed": len(chunk_ids)}


@router.post("/upload")
async def train_from_upload(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    raw = await file.read()
    try:
        content = extract_text_from_upload(file.filename or "", raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    doc_id = str(uuid.uuid4())
    chunk_ids = await ingest_text(doc_id, title, content)

    doc = TrainingDocument(
        id=doc_id,
        title=title,
        source_type="file",
        original_filename=file.filename,
        content=content,
        chunk_ids=chunk_ids,
        chunk_count=len(chunk_ids),
    )
    db.add(doc)
    await db.commit()

    return {"id": doc_id, "chunks_indexed": len(chunk_ids)}


@router.get("/documents")
async def list_training_documents(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(TrainingDocument).order_by(TrainingDocument.createdAt.desc()))
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "source_type": d.source_type,
            "original_filename": d.original_filename,
            "chunk_count": d.chunk_count,
            "createdAt": d.createdAt.isoformat(),
        }
        for d in docs
    ]


@router.delete("/documents/{doc_id}")
async def delete_training_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    doc = await db.get(TrainingDocument, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Training document not found")

    await delete_document(doc.chunk_ids)
    await db.delete(doc)
    await db.commit()

    return {"deleted": doc_id}
