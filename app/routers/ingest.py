# POST /api/v1/ingest — plan.txt section 4 (RAG knowledge base) + section 7 (API contract)
#
# TODO:
#   - protected by X-Internal-Token header (settings.INTERNAL_INGEST_TOKEN),
#     NOT a user JWT — called by cron / future Node webhook
#   - body: {mode: "full" | "incremental"}
#   - calls app.rag.ingest.run(mode)
#   - returns {documents_indexed, duration_ms}
