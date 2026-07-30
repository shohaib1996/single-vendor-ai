# Customer agent tools — plan.txt section 5. Every tool that touches user
# data enforces ownership itself (WHERE userId = state.user_id) — do NOT
# rely on the backend's GET/PATCH/DELETE /orders/:id (no auth/ownership
# check there today, see plan.txt section 1 + section 10).
#
# TODO:
#   def get_my_orders(user_id: str, status: str | None = None) -> list[dict]
#       direct DB query against app.db.store_models.Order, scoped to user_id
#       (this also fixes the backend's missing server-side status filter)
#   def get_order_detail(user_id: str, order_id: str) -> dict | None
#       WHERE id = order_id AND userId = user_id — never another user's order
#   def search_products(query, category=None, brand=None, price_min=None,
#                        price_max=None) -> list[dict]
#       httpx call to {NODE_API_BASE_URL}/products (public endpoint, reuse
#       its existing filter logic instead of re-implementing it)
#   def get_product_details(product_id: str) -> dict
#       httpx call to {NODE_API_BASE_URL}/products/{product_id}
#   def rag_search(query: str) -> list[dict]
#       app.rag.retriever similarity search over kb_documents/product/QnA
