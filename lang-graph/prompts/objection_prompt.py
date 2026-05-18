OBJECTION_CLASSIFY_PROMPT = """
Classify the user's objection into ONE category. Return strict JSON.

Categories:
- price        : worried about cost, "too expensive", "can I get a discount"
- hesitation   : "let me think", "I'll get back to you", "not sure yet"
- value_doubt  : doubting whether the service is worth it
- other        : anything else (or unclear)

OUTPUT (JSON only):
{"objection": "<price|hesitation|value_doubt|other>"}

USER MESSAGE:
{user_message}
"""


OBJECTION_RESPONSE_PROMPT = """
You handle an objection from a customer of a dog grooming business named "{brand_name}".

The customer's objection category is: {objection_category}

A relevant snippet you can lean on (use it as inspiration, do not quote verbatim):
"{snippet}"

The customer's last message:
"{user_message}"

Their selected/recommended service (if any):
{service_summary}

Respond in 2-4 short sentences:
1. Acknowledge their concern warmly.
2. Briefly explain the value (coat condition, gentle handling, transparent pricing).
3. If a cheaper or alternative service would fit, offer it by name.
4. End with a soft next-step question (e.g., "Would you like to see a lighter package?").

Plain text only. No JSON, no markdown.
"""
