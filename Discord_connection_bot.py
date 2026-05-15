import discord
import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Missing DISCORD_TOKEN or GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("models/gemini-2.5-pro")

# -----------------------------
# Logging setup
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("grooming-bot")

# -----------------------------
# Discord setup
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# -----------------------------
# Memory store
# -----------------------------
user_sessions = {}

# -----------------------------
# STRICT STRUCTURE PROMPT
# -----------------------------
SYSTEM_PROMPT = """
You are a professional data extraction assistant for a dog grooming booking system.

You MUST extract information from user messages and follow STRICT JSON format.

AVAILABLE ATTRIBUTES:

Customer:
- name (string)
- phone (string)

- note (string, optional: any specific instructions or notes)

Pet:
- name (string)
- breed (string)
- weight (string, in kg if possible)
- age (string, e.g. "6 months", "2 years")
- coat (string, e.g. "matted", "smooth", "curly")

----------------------------
RULES (VERY IMPORTANT):
----------------------------

1. Always extract whatever information is present (even partial).
2. Never ignore uncertain but likely values.
3. Never ask for ALL fields again.
4. Only ask for missing fields.
5. Be concise and professional.
6. Output MUST be valid JSON only.

----------------------------
OUTPUT FORMAT:
----------------------------

Return EXACTLY this structure:

{
  "data": {
    "name": "",
    "phone": "",
        "note": "",
    "pet": {
      "name": "",
      "breed": "",
      "weight": "",
      "age": "",
      "coat": ""
    }
  },
  "message": "string to user asking only for missing fields"
}

----------------------------
MESSAGE RULE:
----------------------------

- If anything is missing → ask ONLY for missing fields
- If everything is complete → say: "All details received. We will proceed with your booking."
"""


# -----------------------------
# Gemini call
# -----------------------------
def call_gemini(session, user_message):
    prompt = f"""
{SYSTEM_PROMPT}

CURRENT SESSION STATE:
{json.dumps(session, indent=2)}

USER MESSAGE:
{user_message}
"""

    logger.info("Sending request to Gemini")
    logger.debug(f"Prompt: {prompt}")

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.9
        }
    )

    logger.info("Received response from Gemini"  + f"(message: {response})")

    return response.text


# -----------------------------
# Safe update
# -----------------------------
def update_session(session, data):
    if data.get("name"):
        session["name"] = data["name"]

    if data.get("phone"):
        session["phone"] = data["phone"]

    if data.get("note"):
        session["note"] = data["note"]

    pet = data.get("pet", {})

    for field in ["name", "breed", "weight", "age", "coat"]:
        if pet.get(field):
            session["pet"][field] = pet[field]

    return session


# -----------------------------
# Bot events
# -----------------------------
@client.event
async def on_ready():
    logger.info(f"Bot started as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not isinstance(message.channel, discord.DMChannel):
        return

    user_id = str(message.author.id)

    logger.info(f"Message from {user_id}: {message.content}")

    # init session
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "name": "",
            "phone": "",
            "note": "",
            "pet": {
                "breed": "",
                "weight": "",
                "age": "",
                "coat": ""
            }
        }

    session = user_sessions[user_id]

    try:
        raw = call_gemini(session, message.content)

        logger.debug(f"Raw Gemini output: {raw}")

        # Remove markdown code fences if present
        cleaned = raw.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "", 1)

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        logger.debug(f"Cleaned Gemini output: {cleaned}")

        data = json.loads(cleaned)

    except Exception as e:
        logger.error(f"Parsing error: {str(e)}")

        await message.channel.send(
            "I couldn't process that properly. Please provide missing details:\n"
            "- name\n- phone\n- pet name\n- pet breed\n- pet weight\n- pet age\n- pet coat\n- special notes (optional)"
        )
        return

    extracted = data.get("data", {})
    reply = data.get("message", "Please provide missing details.")

    # update session
    session = update_session(session, extracted)
    user_sessions[user_id] = session

    logger.info(f"Updated session: {session}")

    await message.channel.send(reply)


client.run(DISCORD_TOKEN)