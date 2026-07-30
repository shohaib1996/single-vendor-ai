# LangGraph checkpointer setup — plan.txt section 5 + section 12 (open decision:
# Postgres checkpointer vs Redis — pick one).
#
# TODO:
#   Postgres option: langgraph.checkpoint.postgres.AsyncPostgresSaver,
#     pointed at settings.DATABASE_URL, tables in the "ai_chat" schema
#   Redis option: a Redis-backed checkpointer, pointed at settings.REDIS_URL
