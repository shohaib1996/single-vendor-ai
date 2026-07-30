# LLM client factory — plan.txt section 8 (DECIDED: OpenAI)
#
# TODO:
#   from langchain_openai import ChatOpenAI
#   def get_customer_llm() -> ChatOpenAI(model="gpt-4o-mini", ...)
#   def get_admin_llm()    -> ChatOpenAI(model="gpt-4o", ...)
# Keep this the ONLY place that names a specific model, so swapping models
# (or providers) later never touches agent/graph code.
