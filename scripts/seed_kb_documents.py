# One-off script to seed initial ai_chat.kb_documents rows (shipping,
# returns, payment methods, warranty FAQs) — plan.txt section 4.
# Run with: uv run python scripts/seed_kb_documents.py
#
# TODO: write the actual FAQ/policy content and insert via
# app.db.ai_models.KbDocument, then run app.rag.ingest to index it.
