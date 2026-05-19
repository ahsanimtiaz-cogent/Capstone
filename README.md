# Pet Grooming Services Assistant

A conversational AI-powered Discord bot that handles the full customer journey for a pet grooming business — from lead qualification through service selection to real calendar booking — built with LangGraph, Google Gemini, and the Google Workspace APIs.

---

## Features

- **Lead Qualification** — Collects customer name, phone, city, and pet details through natural conversation
- **Service Recommendation** — Matches the right grooming package based on breed and weight using configurable pricing brackets
- **Live Appointment Booking** — Reads real Google Calendar availability and creates confirmed events
- **FAQ Handling** — Answers business questions (hours, location, pricing) using brand config data
- **Objection Handling** — Responds to price concerns and schedules automatic follow-up DMs via APScheduler
- **Persistent Sessions** — Survives bot restarts; per-user state is cached locally and rebuilt from Google Sheets on restart
- **Transactional Safety** — Calendar event creation and Sheets write are atomic; Calendar is rolled back if the Sheets write fails
- **Eval Suite** — Five pytest test cases run fully offline against in-memory fakes

---

## Tech Stack

| Layer | Technology |
|---|---|
| Conversational AI | [LangGraph](https://github.com/langchain-ai/langgraph) + [Google Gemini 2.5 Pro](https://deepmind.google/technologies/gemini/) |
| Bot Transport | [discord.py 2.4](https://discordpy.readthedocs.io/) |
| Persistence | [Google Sheets](https://developers.google.com/sheets) via [gspread](https://gspread.readthedocs.io/) |
| Calendar | [Google Calendar API](https://developers.google.com/calendar) (OAuth 2.0) |
| Scheduling | [APScheduler](https://apscheduler.readthedocs.io/) |
| Runtime | Python 3.9+ |

---

## Project Structure

```
Capstone/
├── lang-graph/                  # Main application (LangGraph implementation)
│   ├── main.py                  # Entry point — wires all services and starts the bot
│   ├── bot/
│   │   ├── discord_client.py    # Discord client setup
│   │   └── handlers.py          # Session routing and message chunking
│   ├── graph/
│   │   ├── state.py             # GroomingState TypedDict, Stages and Intents enums
│   │   ├── workflow.py          # build_graph() — assembles the full LangGraph DAG
│   │   ├── nodes/               # One file per business action node
│   │   └── routers/             # Conditional edge logic (intent / completion / booking)
│   ├── services/
│   │   ├── llm_service.py       # Gemini wrapper with JSON retry logic
│   │   ├── sheets_service.py    # Google Sheets CRUD (Leads, Pets, Services, Appointments)
│   │   ├── calendar_service.py  # Slot discovery, event creation/deletion
│   │   ├── reminder_service.py  # APScheduler follow-up DMs with disk persistence
│   │   └── matching_service.py  # Breed/weight service matching
│   ├── prompts/                 # Gemini prompt templates
│   ├── storage/
│   │   ├── sessions.json        # Runtime per-user session cache
│   │   └── followups.json       # Pending follow-up job list
│   └── evals/                   # pytest suite (runs fully offline)
│
├── Sheets/                      # Sample CSV data for initial sheet population
│   ├── services.csv
│   ├── leads.csv
│   ├── pets.csv
│   ├── appointments.csv
│   └── BrandConfig.csv
│
├── documentation/               # Setup guides for external services
│   ├── make-discord-bit.md      # How to create and configure the Discord bot
│   ├── dicord-bot-add-to-server.md
│   └── claender-api-documentation.md
│
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variable template
```

---

## Prerequisites

- Python **3.9+**
- A **Discord bot token** — [guide](documentation/make-discord-bit.md)
- A **Google Cloud project** with the following APIs enabled:
  - Google Sheets API
  - Google Calendar API
- A **Google Service Account** with a downloaded JSON key (for Sheets access)
- **Google OAuth 2.0 credentials** (`credentials.json`) for Calendar access
- A **Google Gemini API key**

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/ahsanimtiaz-cogent/Capstone.git
cd Capstone
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the template and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/google-key.json
GOOGLE_CALENDAR_ID=primary
```

### 3. Set up Google Sheets

Create a Google Sheet and share it with your service account email (with Editor access).

The sheet must contain these **five worksheets** with exact column headers:

**Leads**
```
lead_id | created_at | source | discord_user_id | name | phone | city | status
```

**Services**
```
service_id | title | description | base_price | duration_min | breed_modifier_json | weight_brackets_json | upsells_json
```

**Pets**
```
lead_id | pet_id | name | species | breed | weight | age | coat | notes
```

**Appointments**
```
appt_id | lead_id | service_id | status | scheduled_at_iso | calendar_event_id
```

**BrandConfig**
```
brand_id | brand_name | welcome_copy | hours | location | timezone | upsells_json | objection_snippets_json
```

Sample data for each sheet is provided in the [`Sheets/`](Sheets/) folder as CSV files.

### 4. Authorize Google Calendar (one-time)

Place your OAuth `credentials.json` in the project root, then run the bot once:

```bash
python lang-graph/main.py
```

A browser window will open for Google OAuth consent. After authorization, a `token.pickle` file is saved locally — the bot reuses it on subsequent runs. Both `credentials.json` and `token.pickle` are in `.gitignore` and should never be committed.

---

## Running the Bot

```bash
source venv/bin/activate
python lang-graph/main.py
```

The bot logs to stdout. DM it from Discord to start a conversation.

---

## Running Tests

The eval suite runs fully offline using in-memory fakes — no API keys required.

```bash
python -m pytest lang-graph/evals/ -v
```

| Test File | Scenario |
|---|---|
| `test_standard_booking.py` | Full happy path: qualify → service → book |
| `test_missing_info.py` | Bot keeps asking until all fields are collected |
| `test_service_not_found.py` | Fallback service for out-of-bracket pet |
| `test_objection.py` | Price objection triggers objection branch |
| `test_followup.py` | Hesitation schedules a 24h follow-up DM |

---

## Conversation Flow

```
User DM
  ↓
detect_intent  (Gemini classifies: qualification | service_inquiry | booking | faq | objection)
  │
  ├─ qualification   → extract info → ask for missing fields → qualify lead
  │
  ├─ service_inquiry → show available services → let user select
  │
  ├─ booking         → ask for day → fetch live Calendar slots → confirm & create event
  │
  ├─ faq             → answer from BrandConfig (hours, location, pricing)
  │
  └─ objection       → empathetic response → schedule 24h follow-up DM
```

The router is stage-aware: if a user is mid-booking-flow, their reply is interpreted as a date/time input regardless of what Gemini would otherwise classify it as.

---

## Key Design Decisions

**Transactional booking** — `create_event` (Calendar) runs first, followed by `append_appointment` (Sheets). If the Sheets write fails, the Calendar event is immediately deleted before raising the error.

**Overlap validation (3-layer)** — Slot availability is checked when fetching slots, again immediately before booking (race-condition guard), and a third time to prevent same-lead double-booking.

**LLM robustness** — `invoke_json()` retries up to 3 times when Gemini returns malformed JSON, appending a correction prompt each time.

**Session persistence** — `storage/sessions.json` is a runtime cache only. Deleting it is safe; the bot reconstructs session state from Sheets on the next message.

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Bot token from the Discord Developer Portal |
| `GEMINI_API_KEY` | API key from [Google AI Studio](https://aistudio.google.com/) |
| `GOOGLE_SHEET_ID` | The ID from your Google Sheet URL |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Absolute path to the service account JSON key file |
| `GOOGLE_CALENDAR_ID` | Calendar to book into (`primary` for your main calendar) |

---

## Security Notes

The following files contain credentials and are excluded from version control via `.gitignore`. Never commit them:

- `.env`
- `google-key.json`
- `credentials.json`
- `token.pickle` / `token.json`

If you believe a token has been exposed, revoke it immediately in the [Google Cloud Console](https://console.cloud.google.com/) and re-run the OAuth flow to generate a fresh token.
