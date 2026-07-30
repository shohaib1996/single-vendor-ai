# LangGraph state schema for the customer agent — plan.txt section 5
#
# TODO:
#   class CustomerAgentState(TypedDict):
#       messages: Annotated[list, add_messages]
#       user_id: str | None     # from verified JWT, NEVER from chat text
#       role: str | None        # "USER" | "ADMIN" | None (guest)
#       conversation_id: str
