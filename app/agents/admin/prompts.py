# System prompt for the admin analytics agent — plan.txt section 6
#
# TODO — must instruct the model to:
#   - only report numbers that came from a tool call, never estimate/invent
#   - when a chart would help, populate the "chart" state field as
#     {type: "line"|"bar"|"pie", data: [...]} for the Recharts-based
#     admin frontend to render
