import discord
import os
import json
import logging
import csv
import uuid
import asyncio

from datetime import datetime
from typing import TypedDict, Dict, Any

from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

# =====================================================
# ENV
# =====================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Missing DISCORD_TOKEN or GEMINI_API_KEY")

# =====================================================
# LLM
# =====================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    google_api_key=GEMINI_API_KEY,
    temperature=0.9,
)

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("grooming-bot")

# =====================================================
# DISCORD
# =====================================================

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# =====================================================
# MEMORY STORE
# =====================================================

user_sessions = {}

# =====================================================
# FILES
# =====================================================

LEADS_FILE = "/Users/cogent/Ai Training/Capstone/Sheets/leads.csv"
SERVICES_FILE = "/Users/cogent/Ai Training/Capstone/Sheets/services.csv"
PET_FILE = "/Users/cogent/Ai Training/Capstone/Sheets/pets.csv"

# =====================================================
# STATE
# =====================================================

class GroomingState(TypedDict):
    user_id: str
    user_message: str

    session: Dict[str, Any]

    extracted_data: Dict[str, Any]

    reply: str

    qualified: bool

# =====================================================
# CSV HELPERS
# =====================================================

def load_leads():
    if not os.path.exists(LEADS_FILE):
        return []

    with open(LEADS_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_leads(leads):
    with open(LEADS_FILE, "w", newline="", encoding="utf-8") as f:

        fieldnames = [
            "lead_id",
            "created_at_iso",
            "source",
            "discord_user_id",
            "name",
            "phone",
            "city",
            "status"
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(leads)


def update_lead(user_id, session):

    leads = load_leads()

    for lead in leads:
        if lead["discord_user_id"] == user_id:
            lead["name"] = session.get("name", "")
            lead["phone"] = session.get("phone", "")

    save_leads(leads)


def get_or_create_lead(user_id, session):

    leads = load_leads()

    for lead in leads:
        if lead["discord_user_id"] == user_id:
            return lead, leads

    new_lead = {
        "lead_id": "LEAD" + uuid.uuid4().hex[:6].upper(),
        "created_at_iso": datetime.now().isoformat(),
        "source": "discord",
        "discord_user_id": user_id,
        "name": session.get("name", ""),
        "phone": session.get("phone", ""),
        "city": "",
        "status": "initiated"
    }

    leads.append(new_lead)

    save_leads(leads)

    return new_lead, leads


def mark_qualified(user_id):

    leads = load_leads()

    for lead in leads:
        if lead["discord_user_id"] == user_id:
            lead["status"] = "qualified"

    save_leads(leads)

# =====================================================
# PET
# =====================================================

def save_pet_record(lead_id, session):

    if not os.path.exists(PET_FILE):
        pets = []

    else:
        with open(PET_FILE, newline="", encoding="utf-8") as f:
            pets = list(csv.DictReader(f))

    pet = {
        "lead_id": lead_id,
        "pet_id": "PET" + uuid.uuid4().hex[:6].upper(),
        "pet_name": session.get("pet", {}).get("name", ""),
        "species": "dog",
        "breed": session.get("pet", {}).get("breed", ""),
        "weight_kg": session.get("pet", {}).get("weight", ""),
        "age_years": session.get("pet", {}).get("age", ""),
        "coat_condition": session.get("pet", {}).get("coat", ""),
        "notes": session.get("note", "")
    }

    pets.append(pet)

    with open(PET_FILE, "w", newline="", encoding="utf-8") as f:

        fieldnames = [
            "lead_id",
            "pet_id",
            "pet_name",
            "species",
            "breed",
            "weight_kg",
            "age_years",
            "coat_condition",
            "notes"
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(pets)

# =====================================================
# SERVICES
# =====================================================

def load_services():

    with open(SERVICES_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def format_services(services):

    text = "All details received. You are now qualified.\n\n"
    text += "Available services:\n\n"

    for s in services:

        text += (
            f"{s['service_id']} - {s['title']}\n"
            f"Price: {s['base_price']}\n"
            f"Duration: {s['duration_min']} min\n\n"
        )

    text += "Reply with the Service ID to continue booking."

    return text

# =====================================================
# SYSTEM PROMPT
# =====================================================

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
"""

# =====================================================
# SESSION UPDATE
# =====================================================

def update_session(session, data):

    if data.get("phone"):
        session["phone"] = data["phone"]

    if data.get("note"):
        session["note"] = data["note"]

    pet = data.get("pet", {})

    for field in ["name", "breed", "weight", "age", "coat"]:

        if pet.get(field):
            session["pet"][field] = pet[field]

    return session

# =====================================================
# COMPLETION CHECK
# =====================================================

def is_complete(session):

    if not session.get("phone"):
        return False

    pet = session.get("pet", {})

    return all(
        pet.get(f)
        for f in ["name", "breed", "weight", "age", "coat"]
    )

# =====================================================
# LANGGRAPH NODES
# =====================================================

def extract_information_node(state: GroomingState):

    prompt = f"""
{SYSTEM_PROMPT}

CURRENT SESSION STATE:
{json.dumps(state["session"], indent=2)}

USER MESSAGE:
{state["user_message"]}
"""

    response = llm.invoke(prompt)

    cleaned = response.content.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1)

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    data = json.loads(cleaned)

    return {
        "extracted_data": data.get("data", {}),
        "reply": data.get("message", "")
    }


def update_session_node(state: GroomingState):

    session = update_session(
        state["session"],
        state["extracted_data"]
    )

    update_lead(
        state["user_id"],
        session
    )

    return {
        "session": session
    }


def completion_router(state: GroomingState):

    if is_complete(state["session"]):
        return "qualified"

    return "incomplete"


def ask_missing_fields_node(state: GroomingState):

    return {
        "qualified": False,
        "reply": state["reply"]
    }


def qualify_lead_node(state: GroomingState):

    mark_qualified(state["user_id"])

    lead, _ = get_or_create_lead(
        state["user_id"],
        state["session"]
    )

    save_pet_record(
        lead["lead_id"],
        state["session"]
    )

    services = load_services()

    return {
        "qualified": True,
        "reply": format_services(services)
    }

# =====================================================
# BUILD GRAPH
# =====================================================

builder = StateGraph(GroomingState)

builder.add_node(
    "extract_information",
    extract_information_node
)

builder.add_node(
    "update_session",
    update_session_node
)

builder.add_node(
    "ask_missing_fields",
    ask_missing_fields_node
)

builder.add_node(
    "qualify_lead",
    qualify_lead_node
)

builder.set_entry_point("extract_information")

builder.add_edge(
    "extract_information",
    "update_session"
)

builder.add_conditional_edges(
    "update_session",
    completion_router,
    {
        "qualified": "qualify_lead",
        "incomplete": "ask_missing_fields"
    }
)

builder.add_edge(
    "ask_missing_fields",
    END
)

builder.add_edge(
    "qualify_lead",
    END
)

graph = builder.compile()

# =====================================================
# DISCORD EVENTS
# =====================================================

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

    # =================================================
    # INIT SESSION
    # =================================================

    if user_id not in user_sessions:

        user_sessions[user_id] = {

            "name": message.author.name,

            "phone": "",

            "note": "",

            "pet": {
                "name": "",
                "breed": "",
                "weight": "",
                "age": "",
                "coat": ""
            }
        }

    session = user_sessions[user_id]

    get_or_create_lead(
        user_id,
        session
    )

    # =================================================
    # GRAPH STATE
    # =================================================

    state = {
        "user_id": user_id,
        "user_message": message.content,

        "session": session,

        "extracted_data": {},

        "reply": "",

        "qualified": False
    }

    # =================================================
    # EXECUTE GRAPH
    # =================================================

    try:

        result = await asyncio.to_thread(
            graph.invoke,
            state
        )

    except Exception as e:

        logger.error(f"Graph execution error: {str(e)}")

        await message.channel.send(
            "I couldn't process that properly."
        )

        return

    # =================================================
    # SAVE UPDATED SESSION
    # =================================================

    user_sessions[user_id] = result["session"]

    logger.info(
        f"Updated session: {result['session']}"
    )

    # =================================================
    # SEND REPLY
    # =================================================

    await message.channel.send(
        result["reply"]
    )

# =====================================================
# START BOT
# =====================================================

client.run(DISCORD_TOKEN)