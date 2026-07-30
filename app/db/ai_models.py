# This service's OWN tables — schema="ai_chat", migrated via alembic/
# (never touches Prisma's "public" schema/migrations). See plan.txt
# section 3 and section 4.
#
# TODO:
#   class Conversation(Base): __tablename__ = "conversations"; schema="ai_chat"
#       id, user_id (nullable — guests), channel ("customer"|"admin"), created_at
#   class Message(Base):      __tablename__ = "messages"; schema="ai_chat"
#       id, conversation_id, role ("user"|"assistant"|"tool"), content,
#       tool_calls (JSON), created_at
#   class KbDocument(Base):   __tablename__ = "kb_documents"; schema="ai_chat"
#       id, title, content, category, is_published, updated_at
#   (pgvector embedding tables are managed by langchain-postgres's PGVector
#   class itself — see app/rag/vectorstore.py — not hand-defined here)
