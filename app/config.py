from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Same values as single-vendor-backend/.env — this service reads the
    # same Postgres DB and verifies the same JWTs, so these MUST match.
    DATABASE_URL: str
    JWT_SECRET: str

    # This service's own config
    OPENAI_API_KEY: str
    REDIS_URL: str = "redis://localhost:6379/0"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # RAG vector store — Pinecone (decided over pgvector, see plan.txt
    # section 4 update). Free tier is enough for a store catalog + policy
    # docs. Get a key at app.pinecone.io.
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "single-vendor-kb"

    # Existing Node backend, for tools that reuse its REST endpoints
    # (product search/detail — see plan section 5)
    NODE_API_BASE_URL: str = "http://localhost:5000/api/v1"

    # Shared-secret header for POST /api/v1/ingest — NOT a user JWT
    INTERNAL_INGEST_TOKEN: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
