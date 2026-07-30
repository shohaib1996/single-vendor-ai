# JWT auth dependencies — plan.txt section 2b + section 10 (security)
#
# Mirrors single-vendor-backend/src/app/middleware/auth.ts exactly:
#   - token from `Authorization: Bearer <token>` header only (no cookies)
#   - jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
#   - payload is {id, email, role, iat, exp} — do NOT trust `role` alone,
#     re-fetch the User row from Postgres by id (via app.db.session) to
#     get the CURRENT role, same as the Node middleware does
#   - 401 if token missing/invalid/expired/user not found
#
# TODO:
#   def get_current_user(...) -> the re-fetched User row; used by
#       chat_customer (optional — None for guests)
#   def get_current_admin(...) -> like get_current_user but raises 403
#       unless role == "ADMIN"; used by chat_admin and ingest
