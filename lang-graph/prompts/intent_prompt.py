INTENT_PROMPT = """
You classify a user's Discord message for a dog grooming booking bot.

Choose EXACTLY ONE intent from this list:

- qualification       : The user is starting a request, describing themselves or their pet, or providing details like name, phone, breed, weight, age, coat.
- service_inquiry     : The user is asking what services exist, prices, or what package to pick (without yet ready to book a time).
- booking             : The user wants to actually pick a day/time, see availability, or confirm a booking.
- faq                 : The user is asking about hours, location, contact info, or other business details.
- objection           : The user is hesitating, complaining about price, doubting value, or saying "too expensive", "let me think", etc.

CONTEXT:
- The session may already have collected pet/customer info — if so, plain follow-ups about pet attributes are still `qualification`.
- If the user gives mixed signals, pick the dominant one. Default to `qualification` when unsure and the session is incomplete.

Return STRICT JSON only, no markdown:

{"intent": "<one of: qualification|service_inquiry|booking|faq|objection>"}

USER MESSAGE:
{user_message}

CURRENT SESSION:
{session_json}
"""
