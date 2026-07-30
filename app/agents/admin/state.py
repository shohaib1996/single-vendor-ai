# LangGraph state schema for the admin analytics agent — plan.txt section 6
#
# TODO:
#   class AdminAgentState(TypedDict):
#       messages: Annotated[list, add_messages]
#       user_id: str            # always present — this graph is admin-only
#       conversation_id: str
#       chart: dict | None      # optional {type, data} for the frontend
