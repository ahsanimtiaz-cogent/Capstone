# Pet Grooming Bot — LangGraph Capstone

A LangGraph-driven Discord bot for a dog grooming business. Customers DM the
bot, get qualified, see services with prices and durations from the Services
sheet, and book real Google Calendar appointments — all backed by a Google
Sheet for persistence.

This directory contains the LangGraph implementation of the capstone. The
older single-file prototype (`lang-graph-capstone.py`) is superseded by the
modular layout under this folder.

## Architecture

```
Discord (transport)
    ↓
LangGraph FSM (workflow)
    ↓
Nodes (business actions: extract / qualify / show services / book / etc.)
    ↓
Services Layer
    ├── SheetsRepo      → Google Sheets via gspread
    ├── CalendarService → Google Calendar (OAuth)
    ├── LLMService      → Gemini + safe JSON parsing
    ├── MatchingService → fuzzy + weight-bracket service matching
    └── ReminderService → APScheduler follow-up DMs
```

## Folder layout

```
lang-graph/
├── main.py                  entrypoint
├── bot/                     Discord client + handlers
├── graph/
│   ├── state.py             GroomingState TypedDict + Stages/Intents enums
│   ├── workflow.py          build_graph()
│   ├── nodes/               one node per business action
│   └── routers/             stage-/intent-aware conditional edges
├── services/                Sheets, Calendar, LLM, Reminder, Matching wrappers
├── prompts/                 Gemini prompt templates
├── storage/                 sessions.json + followups.json (runtime cache)
└── evals/                   pytest test cases against in-memory fakes
```

## Setup

1. Activate your virtualenv and install deps:
   ```
   pip install -r requirements.txt
   ```
2. `.env` (project root) must define:
   ```
   DISCORD_TOKEN=...
   GEMINI_API_KEY=...
   GOOGLE_SHEET_ID=...
   GOOGLE_SERVICE_ACCOUNT_FILE=/abs/path/to/google-key.json
   GOOGLE_CALENDAR_ID=primary
   ```
3. **One-time sheet update**: the **Appointments** worksheet must have these
   columns in its header row (in any order):
   ```
   appt_id, lead_id, service_id, status, scheduled_at_iso, calendar_event_id
   ```
   `scheduled_at_iso` and `calendar_event_id` extend the original ERD — see
   "ERD deviation" below. The bot fails fast at startup with a clear error if
   these columns are missing.
4. First run of Calendar will trigger an OAuth browser flow and cache the
   token to `token.pickle` at the project root.

## Run

```
python lang-graph/main.py
```

DM the bot from Discord. The bot logs to stdout.

## Run evals

```
python -m pytest lang-graph/evals/ -v
```

The eval suite uses in-memory fakes (`evals/fakes.py`) so it runs offline and
deterministically. Each test maps to one of the five acceptance test cases:

| File                          | Test Case                                    |
|-------------------------------|----------------------------------------------|
| `test_standard_booking.py`    | 1 — full happy path to confirmed booking     |
| `test_missing_info.py`        | 2 — bot keeps asking until qualified         |
| `test_service_not_found.py`   | 3 — fallback service for out-of-bracket pet  |
| `test_objection.py`           | 4 — "too expensive" → objection branch       |
| `test_followup.py`            | 5 — hesitation schedules a follow-up DM      |

## Graph topology

```
START → detect_intent → intent_router
  ├ qualification → extract → update_session → completion_router
  │                                             ├ incomplete → ask_missing → END
  │                                             └ qualified  → qualify_lead → END
  ├ service_inquiry → service_inquiry_dispatch
  │                     ├ show_services → END
  │                     └ select_service → END
  ├ booking → booking_dispatch
  │            ├ extract       (not yet qualified → fall back to qualification)
  │            ├ show_services (qualified, no service picked)
  │            ├ select_service (mid service-selection)
  │            ├ show_hours    (just qualified, ready to ask for day)
  │            ├ fetch_slots   (day picked, need times)
  │            ├ book          (time picked, create event + write appt)
  │            └ end           (already booked)
  ├ faq → faq → END
  └ objection → objection → schedule_followup → END
```

## Overlap-validation defense in depth (Phase 4 / 8)

A `[start, start + duration_min)` window is considered free when, for every
existing event `[E_start, E_end)`, either `start + duration_min <= E_start`
or `start >= E_end`, **and** the window fits inside business hours
(`hours` in BrandConfig). This check is applied three times:

1. `fetch_slots` only emits start times that pass it.
2. `book_appointment` re-runs it against fresh Calendar state right before
   booking (race-condition guard).
3. `book_appointment` also checks the lead's own existing APPOINTMENTS rows
   for window overlap (same-lead double-booking guard).

If any check fails, the user is told why and offered fresh slots — never
silently dropped.

## Transactional booking

`create_event` (Calendar) and `append_appointment` (Sheet) are wrapped in a
try/except pair. If the sheet write fails after the event was created, the
Calendar event is deleted (`calendar.delete_event(event_id)`) before raising.

## Follow-ups (Phase 7)

`ReminderService` wraps `apscheduler.AsyncIOScheduler` and persists pending
jobs to `storage/followups.json`. On bot restart, it rehydrates pending jobs
from disk. Jobs fire callbacks that DM the user via Discord.

## ERD deviation

The original ERD lists APPOINTMENTS as `{appt_id, lead_id, service_id, status}`.
This implementation **extends** APPOINTMENTS with two columns:

- `scheduled_at_iso` — ISO-8601 booking start time
- `calendar_event_id` — Google Calendar event ID, for transactional rollback
  and re-sync

Without these columns the bot cannot fulfil the "bookings appear in both
Calendar and Sheet" acceptance criterion in a transactional way. The
deviation is documented in `lang-graph/ERD.io`.

## Notes / known constraints

- Python 3.9+ (uses `zoneinfo`).
- The Sheets schema is the system of record; `storage/sessions.json` is a
  per-user runtime cache that exists so a DM mid-flow doesn't lose state on
  bot restart. Deleting it is safe — the bot rebuilds from Sheets.
- Discord's 2000-char message cap is handled by chunking in `bot/handlers.py`.
- `safe_json_parse` (in `services/llm_service.py`) retries Gemini up to 3
  times when the model returns malformed JSON.
