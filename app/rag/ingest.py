# Ingestion pipeline — plan.txt section 4. Runnable standalone:
#   uv run python -m app.rag.ingest --mode full
#
# TODO:
#   def run(mode: Literal["full", "incremental"]) -> {documents_indexed, duration_ms}
#     1. pull rows via app.rag.loaders (per source type)
#     2. embed + upsert into PGVector (app.rag.vectorstore)
#        - delete-then-insert keyed on a stable metadata id (e.g. product_id)
#          so re-running is idempotent
#     3. "incremental" = only rows where updatedAt > last successful run
#
# Also called from app/routers/ingest.py (POST /api/v1/ingest) and can be
# scheduled with APScheduler for a nightly full run (see plan.txt Phase 1/5).
if __name__ == "__main__":
    raise NotImplementedError("see TODOs above")
