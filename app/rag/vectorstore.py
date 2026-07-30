# PGVector setup — plan.txt section 4. DECIDED: pgvector on the existing
# Neon Postgres DB (schema="ai_chat"), via langchain-postgres.
#
# TODO:
#   - requires `CREATE EXTENSION IF NOT EXISTS vector;` run once on Neon
#   - from langchain_openai import OpenAIEmbeddings
#   - from langchain_postgres import PGVector
#   - one collection per content type (products, kb_documents, product_qna)
#     or one collection with a "type" metadata field — pick one and be
#     consistent with retriever.py's filtering
