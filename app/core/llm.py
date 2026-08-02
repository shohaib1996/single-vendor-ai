# LLM client factory — plan.txt section 8 (DECIDED: OpenAI). Keep this the
# ONLY place that names a specific model, so swapping models/providers
# later never touches agent/graph code.

from langchain_openai import ChatOpenAI

from app.config import settings


def get_customer_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0)


def get_admin_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0)
