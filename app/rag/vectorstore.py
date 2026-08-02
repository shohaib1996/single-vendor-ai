# Pinecone vector store — plan.txt section 4 (DECIDED: Pinecone, not
# pgvector — user's call, index already created manually in the Pinecone
# console: "single-vendor-kb", 1024 dimensions, cosine metric).
#
# EMBEDDING_DIMENSIONS=1024 below matches that index exactly.
# text-embedding-3-small defaults to 1536-dim but supports an explicit
# `dimensions` param to truncate its output — this avoids needing to
# recreate the index at a different size.

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from app.config import settings

EMBEDDING_DIMENSIONS = 1024

_pc = Pinecone(api_key=settings.PINECONE_API_KEY)


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        dimensions=EMBEDDING_DIMENSIONS,
        api_key=settings.OPENAI_API_KEY,
    )


def get_vectorstore() -> PineconeVectorStore:
    index = _pc.Index(settings.PINECONE_INDEX_NAME)
    return PineconeVectorStore(index=index, embedding=get_embeddings())
