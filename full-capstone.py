import discord
import os
import json
import logging
import uuid
import asyncio
import difflib

from datetime import datetime, timedelta
from typing import TypedDict, Dict, Any, List

from dotenv import load_dotenv

from langgraph.graph import StateGraph, END

from langchain_google_genai import ChatGoogleGenerativeAI

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import pickle

import gspread
from google.oauth2.service_account import Credentials as GS_Credentials

# =====================================================
# ENV
# =====================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

if not DISCORD_TOKEN:
    raise ValueError("Missing DISCORD_TOKEN")

if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY")

if not GOOGLE_SHEET_ID:
    raise ValueError("Missing GOOGLE_SHEET_ID")

if not GOOGLE_SERVICE_ACCOUNT_FILE:
    raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_FILE")

if not GOOGLE_CALENDAR_ID:
    raise ValueError("Missing GOOGLE_CALENDAR_ID")

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("grooming-agent")

# =====================================================
# DISCORD
# =====================================================

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

client = discord.Client(intents=intents)

# =====================================================
# LLM
# =====================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    google_api_key=GEMINI_API_KEY,
    temperature=0.6,
)

# =====================================================
# SESSION STORAGE
# =====================================================

SESSIONS_FILE = "sessions.json"


def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}

    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


user_sessions = load_sessions()



def save_sessions():
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_sessions, f, indent=2)

# =====================================================
# GOOGLE SHEETS
# =====================================================

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

sheet_creds = GS_Credentials.from_service_account_file(
    GOOGLE_SERVICE_ACCOUNT_FILE,
    scopes=SHEETS_SCOPES
)

sheet_client = gspread.authorize(sheet_creds)
spreadsheet = sheet_client.open_by_key(GOOGLE_SHEET_ID)

LEADS_SHEET = spreadsheet.worksheet("Leads")
SERVICES_SHEET = spreadsheet.worksheet("Services")
PETS_SHEET = spreadsheet.worksheet("Pets")
APPOINTMENTS_SHEET = spreadsheet.worksheet("Appointments")
BRAND_CONFIG_SHEET = spreadsheet.worksheet("BrandConfig")

# =====================================================
# GOOGLE CALENDAR
# =====================================================

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                CALENDAR_SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)


calendar_service = get_calendar_service()

# =====================================================
# FSM STAGES
# =====================================================

class Stages:
    INITIATED = "initiated"
    QUALIFYING = "qualifying"
    QUALIFIED = "qualified"
    SERVICE_SELECTION = "service_selection"
    BOOKING_DAY = "booking_day"
    BOOKING_SLOT = "booking_slot"
    BOOKED = "booked"
    FOLLOWUP_PENDING = "followup_pending"

# =====================================================
# STATE
# =====================================================

class GroomingState(TypedDict):
    user_id: str
    user_message: str
    session: Dict[str, Any]
    intent: str
    extracted_data: Dict[str, Any]
    reply: str
    selected_service: Dict[str, Any]
    available_slots: List[str]
    booking_day: str
    booking_time: str
    booking_confirmed: bool

# =====================================================
# HELPERS
# =====================================================


def get_sheet_records(sheet):
    return sheet.get_all_records()



def append_sheet_record(sheet, row):
    sheet.append_row(row)



def update_lead_status(user_id, status):
    records = LEADS_SHEET.get_all_records()

    for index, record in enumerate(records, start=2):
        if str(record.get("discord_user_id")) == str(user_id):
            LEADS_SHEET.update_cell(index, 8, status)
            return



def update_lead_info(user_id, session):
    records = LEADS_SHEET.get_all_records()

    for index, record in enumerate(records, start=2):
        if str(record.get("discord_user_id")) == str(user_id):
            LEADS_SHEET.update_cell(index, 5, session.get("name", ""))
            LEADS_SHEET.update_cell(index, 6, session.get("phone", ""))
            return



def get_or_create_lead(user_id, session):
    records = LEADS_SHEET.get_all_records()

    for record in records:
        if str(record.get("discord_user_id")) == str(user_id):
            return record

    lead_id = "LEAD" + uuid.uuid4().hex[:6].upper()

    row = [
        lead_id,
        datetime.now().isoformat(),
        "discord",
        str(user_id),
        session.get("name", ""),
        session.get("phone", ""),
        "",
        "initiated"
    ]

    append_sheet_record(LEADS_SHEET, row)

    return {
        "lead_id": lead_id
    }



def save_pet_record(lead_id, session):
    pet = session.get("pet", {})

    row = [
        lead_id,
        "PET" + uuid.uuid4().hex[:6].upper(),
        pet.get("name", ""),
        "dog",
        pet.get("breed", ""),
        pet.get("weight", ""),
        pet.get("age", ""),
        pet.get("coat", ""),
        session.get("note", "")
    ]

    append_sheet_record(PETS_SHEET, row)



def load_services():
    return SERVICES_SHEET.get_all_records()



def load_brand_config():
    records = BRAND_CONFIG_SHEET.get_all_records()

    config = {}

    for item in records:
        config[item["key"]] = item["value"]

    return config



def is_complete(session):
    if not session.get("phone"):
        return False

    pet = session.get("pet", {})

    required = [
        "name",
        "breed",
        "weight",
        "age",
        "coat"
    ]

    return all(pet.get(field) for field in required)



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
# INTENT DETECTION
# =====================================================

INTENT_PROMPT = """
You are an intent classifier.

Possible intents:
- qualification
- faq
- booking
- objection
- service_selection

Return ONLY JSON.

Format:
{
  "intent": "qualification"
}
"""

# =====================================================
# EXTRACTION PROMPT
# =====================================================

EXTRACTION_PROMPT = """
You are a professional data extraction assistant for a dog grooming booking system.

Extract all customer and pet information.

Return ONLY JSON.

Format:
{
  "data": {
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
  "message": "reply"
}
"""

# =====================================================
# FAQ PROMPT
# =====================================================

FAQ_PROMPT = """
You are a grooming business assistant.

Use ONLY provided business information.

BUSINESS INFO:
{config}

Question:
{question}
"""

# =====================================================
# OBJECTION PROMPT
# =====================================================

OBJECTION_PROMPT = """
You are a grooming sales assistant.

Respond professionally to pricing objections.

Keep response concise.

Customer message:
{message}
"""

# =====================================================
# BOOKING HELPERS
# =====================================================


def generate_available_slots(day_string):
    config = load_brand_config()

    opening = config.get("opening_time", "09:00")
    closing = config.get("closing_time", "17:00")

    start_hour = int(opening.split(":")[0])
    end_hour = int(closing.split(":")[0])

    slots = []

    target_date = datetime.strptime(day_string, "%Y-%m-%d")

    existing_events = calendar_service.events().list(
        calendarId=GOOGLE_CALENDAR_ID,
        timeMin=target_date.isoformat() + "Z",
        timeMax=(target_date + timedelta(days=1)).isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    busy_hours = []

    for event in existing_events.get("items", []):
        start = event["start"].get("dateTime")

        if start:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            busy_hours.append(dt.hour)

    for hour in range(start_hour, end_hour):
        if hour not in busy_hours:
            slots.append(f"{hour}:00")

    return slots



def create_calendar_booking(user_id, session, service, day, time_slot):
    start_datetime = datetime.strptime(
        f"{day} {time_slot}",
        "%Y-%m-%d %H:%M"
    )

    duration = int(service.get("duration_min", 60))

    end_datetime = start_datetime + timedelta(minutes=duration)

    event = {
        "summary": f"Dog Grooming - {session['pet']['name']}",
        "description": f"Customer: {session['name']}",
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": "UTC"
        }
    }

    created_event = calendar_service.events().insert(
        calendarId=GOOGLE_CALENDAR_ID,
        body=event
    ).execute()

    row = [
        "BOOK" + uuid.uuid4().hex[:6].upper(),
        str(user_id),
        service.get("service_id"),
        day,
        time_slot,
        created_event.get("id")
    ]

    append_sheet_record(APPOINTMENTS_SHEET, row)

    update_lead_status(user_id, "booked")

    return created_event

# =====================================================
# SERVICE MATCHING
# =====================================================


def find_best_service(session):
    services = load_services()

    breed = session.get("pet", {}).get("breed", "")

    titles = [s.get("title", "") for s in services]

    matches = difflib.get_close_matches(
        breed,
        titles,
        n=1,
        cutoff=0.1
    )

    if matches:
        for service in services:
            if service["title"] == matches[0]:
                return service

    return services[0] if services else None

# =====================================================
# FOLLOWUP
# =====================================================


def schedule_followup(session):
    session["followup_required"] = True
    session["followup_time"] = (
        datetime.now() + timedelta(hours=24)
    ).isoformat()

    return session

# =====================================================
# LANGGRAPH NODES
# =====================================================


def detect_intent_node(state: GroomingState):
    prompt = f"""
{INTENT_PROMPT}

USER MESSAGE:
{state['user_message']}
"""

    response = llm.invoke(prompt)

    cleaned = response.content.strip()

    cleaned = cleaned.replace("```json", "")
    cleaned = cleaned.replace("```", "")

    parsed = json.loads(cleaned)

    return {
        "intent": parsed.get("intent", "qualification")
    }



def intent_router(state: GroomingState):
    return state["intent"]



def faq_node(state: GroomingState):
    config = load_brand_config()

    prompt = FAQ_PROMPT.format(
        config=json.dumps(config, indent=2),
        question=state["user_message"]
    )

    response = llm.invoke(prompt)

    return {
        "reply": response.content
    }



def objection_node(state: GroomingState):
    prompt = OBJECTION_PROMPT.format(
        message=state["user_message"]
    )

    response = llm.invoke(prompt)

    return {
        "reply": response.content
    }



def extract_information_node(state: GroomingState):
    prompt = f"""
{EXTRACTION_PROMPT}

CURRENT SESSION:
{json.dumps(state['session'], indent=2)}

USER MESSAGE:
{state['user_message']}
"""

    retries = 3

    for _ in range(retries):
        try:
            response = llm.invoke(prompt)

            cleaned = response.content.strip()
            cleaned = cleaned.replace("```json", "")
            cleaned = cleaned.replace("```", "")

            parsed = json.loads(cleaned)

            return {
                "extracted_data": parsed.get("data", {}),
                "reply": parsed.get("message", "")
            }

        except Exception:
            continue

    return {
        "reply": "I could not process your request."
    }



def update_session_node(state: GroomingState):
    session = update_session(
        state["session"],
        state["extracted_data"]
    )

    session["stage"] = Stages.QUALIFYING

    update_lead_info(
        state["user_id"],
        session
    )

    return {
        "session": session
    }



def qualification_router(state: GroomingState):
    if is_complete(state["session"]):
        return "qualified"

    return "incomplete"



def ask_missing_fields_node(state: GroomingState):
    return {
        "reply": state["reply"]
    }



def qualify_lead_node(state: GroomingState):
    session = state["session"]

    session["stage"] = Stages.QUALIFIED

    update_lead_status(
        state["user_id"],
        "qualified"
    )

    lead = get_or_create_lead(
        state["user_id"],
        session
    )

    save_pet_record(
        lead["lead_id"],
        session
    )

    service = find_best_service(session)

    session["selected_service"] = service

    text = (
        f"You are now qualified.\n\n"
        f"Recommended Service:\n"
        f"{service['service_id']} - {service['title']}\n"
        f"Price: {service['base_price']}\n"
        f"Duration: {service['duration_min']} minutes\n\n"
        f"Would you like to book an appointment?"
    )

    return {
        "session": session,
        "reply": text
    }



def booking_day_node(state: GroomingState):
    session = state["session"]

    session["stage"] = Stages.BOOKING_DAY

    config = load_brand_config()

    working_days = config.get("working_days", "Monday-Friday")
    opening = config.get("opening_time", "09:00")
    closing = config.get("closing_time", "17:00")

    return {
        "reply": (
            f"Our working days are {working_days}.\n"
            f"Hours: {opening} to {closing}.\n\n"
            f"Please provide booking day in YYYY-MM-DD format."
        )
    }



def slot_generation_node(state: GroomingState):
    day = state["user_message"].strip()

    slots = generate_available_slots(day)

    if not slots:
        return {
            "reply": "No slots available for this day. Please choose another day."
        }

    return {
        "available_slots": slots,
        "booking_day": day,
        "reply": (
            "Available slots:\n\n" +
            "\n".join(slots) +
            "\n\nPlease select a time slot."
        )
    }



def confirm_booking_node(state: GroomingState):
    session = state["session"]

    service = session.get("selected_service")

    slot = state["user_message"].strip()

    create_calendar_booking(
        state["user_id"],
        session,
        service,
        state["booking_day"],
        slot
    )

    session["stage"] = Stages.BOOKED

    return {
        "booking_confirmed": True,
        "reply": (
            f"Booking confirmed for {state['booking_day']} at {slot}."
        ),
        "session": session
    }



def followup_node(state: GroomingState):
    session = schedule_followup(state["session"])

    return {
        "session": session,
        "reply": "No problem. I will follow up with you later."
    }

# =====================================================
# ROUTERS
# =====================================================


def booking_router(state: GroomingState):
    message = state["user_message"].lower()

    if "yes" in message or "book" in message:
        return "booking"

    if "think" in message:
        return "followup"

    return "end"

# =====================================================
# BUILD GRAPH
# =====================================================

builder = StateGraph(GroomingState)

builder.add_node("detect_intent", detect_intent_node)
builder.add_node("faq", faq_node)
builder.add_node("objection", objection_node)
builder.add_node("extract_information", extract_information_node)
builder.add_node("update_session", update_session_node)
builder.add_node("ask_missing_fields", ask_missing_fields_node)
builder.add_node("qualify_lead", qualify_lead_node)
builder.add_node("booking_day_node", booking_day_node)
builder.add_node("slot_generation", slot_generation_node)
builder.add_node("confirm_booking", confirm_booking_node)
builder.add_node("followup", followup_node)

builder.set_entry_point("detect_intent")

builder.add_conditional_edges(
    "detect_intent",
    intent_router,
    {
        "qualification": "extract_information",
        "faq": "faq",
        "objection": "objection",
        "booking": "booking_day_node",
        "service_selection": "booking_day_node"
    }
)

builder.add_edge(
    "extract_information",
    "update_session"
)

builder.add_conditional_edges(
    "update_session",
    qualification_router,
    {
        "qualified": "qualify_lead",
        "incomplete": "ask_missing_fields"
    }
)

builder.add_conditional_edges(
    "qualify_lead",
    booking_router,
    {
        "booking": "booking_day_node",
        "followup": "followup",
        "end": END
    }
)

builder.add_edge("booking_day_node", END)
builder.add_edge("slot_generation", END)
builder.add_edge("confirm_booking", END)
builder.add_edge("faq", END)
builder.add_edge("objection", END)
builder.add_edge("ask_missing_fields", END)
builder.add_edge("followup", END)

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

    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "name": message.author.name,
            "phone": "",
            "note": "",
            "stage": Stages.INITIATED,
            "followup_required": False,
            "pet": {
                "name": "",
                "breed": "",
                "weight": "",
                "age": "",
                "coat": ""
            }
        }

    session = user_sessions[user_id]

    get_or_create_lead(user_id, session)

    state = {
        "user_id": user_id,
        "user_message": message.content,
        "session": session,
        "intent": "qualification",
        "extracted_data": {},
        "reply": "",
        "selected_service": {},
        "available_slots": [],
        "booking_day": "",
        "booking_time": "",
        "booking_confirmed": False
    }

    try:
        result = await asyncio.to_thread(
            graph.invoke,
            state
        )

    except Exception as e:
        logger.error(f"Graph execution error: {str(e)}")

        await message.channel.send(
            "An error occurred while processing your request."
        )

        return

    user_sessions[user_id] = result.get(
        "session",
        session
    )

    save_sessions()

    logger.info(f"Updated session: {user_sessions[user_id]}")

    await message.channel.send(
        result.get("reply", "Okay")
    )

# =====================================================
# EVALS
# =====================================================


def run_evals():

    eval_cases = [
        {
            "name": "Standard Booking",
            "input": "Hi I need grooming for my dog Bella",
            "expected": "qualification"
        },
        {
            "name": "Missing Info",
            "input": "I need grooming",
            "expected": "missing_fields"
        },
        {
            "name": "Service Not Found",
            "input": "My rare dog breed needs grooming",
            "expected": "service_recommendation"
        },
        {
            "name": "Objection",
            "input": "That is too expensive",
            "expected": "objection"
        },
        {
            "name": "No Booking Yet",
            "input": "I will think about it",
            "expected": "followup"
        }
    ]

    for case in eval_cases:
        print(f"Running Eval: {case['name']}")

# =====================================================
# START
# =====================================================

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
