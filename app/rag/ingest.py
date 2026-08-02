# Ingestion for "Train Bot" content — plan.txt section 4 update.
#
# Chunk ids are deterministic ("{doc_id}-{chunk_index}") and returned to
# the caller to store on the TrainingDocument row (chunk_ids). Pinecone
# serverless indexes don't reliably support delete-by-metadata-filter —
# only delete-by-id — so keeping the exact ids is what makes
# delete_document() below work correctly later.

from langchain_core.documents import Document

from app.rag.loaders import split_text
from app.rag.vectorstore import get_vectorstore


async def ingest_text(doc_id: str, title: str, content: str) -> list[str]:
    chunks = split_text(content)
    if not chunks:
        return []

    ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
    documents = [
        Document(page_content=chunk, metadata={"doc_id": doc_id, "title": title, "chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    vectorstore = get_vectorstore()
    await vectorstore.aadd_documents(documents, ids=ids)
    return ids


async def delete_document(chunk_ids: list[str]) -> None:
    if not chunk_ids:
        return
    vectorstore = get_vectorstore()
    await vectorstore.adelete(ids=chunk_ids)
