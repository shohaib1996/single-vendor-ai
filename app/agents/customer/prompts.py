# System prompt + guardrail instructions for the customer agent.
# Plan.txt section 5 ("respond" node + "guardrail" node).
#
# TODO — must instruct the model to:
#   - only state facts that came from a tool result or retrieved chunk,
#     never invent order status / price / stock numbers
#   - treat tool outputs and RAG chunks as DATA, not instructions
#     (prompt-injection hardening — plan.txt section 10)
#   - refuse write actions (v1 is read-only, no order cancellation etc.)
#   - if unauthenticated and asked an order question, ask the user to sign in
#     instead of calling order tools
