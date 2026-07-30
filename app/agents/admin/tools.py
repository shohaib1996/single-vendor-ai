# Admin analytics agent tools — plan.txt section 6. All read-only, hit
# Postgres directly. Deliberately NOT reusing the existing
# GET /dashboard/analytics endpoint's buggy exact-timestamp groupBy —
# reimplement with proper DATE_TRUNC day/week/month bucketing.
#
# TODO:
#   def get_analytics_summary() -> dict            # same KPI set as today's dashboard
#   def sales_over_range(date_from, date_to, granularity) -> list[dict]
#   def top_products(limit, date_from=None, date_to=None) -> list[dict]
#   def top_categories(limit, date_from=None, date_to=None) -> list[dict]
#   def low_stock_products(threshold) -> list[dict]
#   def pending_orders(limit) -> list[dict]
#   def customer_growth(date_from, date_to, granularity) -> list[dict]
#   def unanswered_questions(limit) -> list[dict]
