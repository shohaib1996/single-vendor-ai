# DB rows -> LangChain Document objects. Plan.txt section 4.
#
# TODO, one function per source type, each returning list[Document] with
# rich metadata (type, id, category, brand, ...) for later filtering:
#   def load_products(session) -> list[Document]
#   def load_categories(session) -> list[Document]
#   def load_brands(session) -> list[Document]
#   def load_product_qna(session) -> list[Document]   # ANSWERED questions only
#   def load_kb_documents(session) -> list[Document]  # policies/FAQs, split
#       with RecursiveCharacterTextSplitter (~500-800 tokens, ~100 overlap)
#
# Do NOT load Order or User rows here — see plan.txt section 10 (security):
# never put PII/order data into the semantically-searchable index.
