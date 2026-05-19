Your project is already large enough that you should treat it like a real production system and implement it in incremental phases.

For a LangGraph implementation, the best approach is:

```text id="1ukb92"
Build deterministic workflow first
Then add tools/integrations
Then add recovery/followups/evals
```

NOT:

```text id="utx4gj"
Try building entire AI agent at once
```

---

# Recommended Project Phases

---

# Phase 1 — Foundation & Project Setup

## Goal

Prepare clean architecture before building logic.

---

## Deliverables

### 1. Folder Structure

Recommended:

```text id="5o7fdc"
project/
│
├── bot/
│   ├── discord_client.py
│   ├── handlers.py
│
├── graph/
│   ├── state.py
│   ├── workflow.py
│   ├── nodes/
│   ├── routers/
│
├── services/
│   ├── sheets_service.py
│   ├── calendar_service.py
│   ├── reminder_service.py
│
├── prompts/
│   ├── extraction_prompt.py
│   ├── objection_prompt.py
│
├── storage/
│   ├── leads.csv
│   ├── pets.csv
│   ├── services.csv
│   ├── appointments.csv
│   ├── brand_config.csv
│
├── evals/
│
├── main.py
│
├── requirements.txt
│
└── .env
```

---

## Implement

### Discord connection

* DM handling
* session initialization

### Environment setup

* Gemini key
* Discord token

### Logging

### LangGraph base setup

* state
* graph
* nodes
* routers

---

# Phase 2 — Lead Qualification Flow

## Goal

Implement deterministic FSM qualification.

This is your current progress.

---

## Features

### Collect customer:

* name
* phone

### Collect pet:

* breed
* weight
* age
* coat

### Update lead status:

```text id="4yb6j1"
initiated → qualified
```

---

## LangGraph Nodes

```text id="d9uteb"
extract_info_node
update_session_node
missing_fields_router
qualification_router
qualify_lead_node
```

---

## Important Rule

LLM only:

* extracts data
* generates conversational responses

Code controls:

* state
* routing
* validation
* qualification

---

# Phase 3 — Services & Pricing Flow

## Goal

Dynamic service recommendations from sheet.

---

## Features

### Read Services sheet dynamically

NO hardcoded pricing.

### Show:

* service
* duration
* price

### Handle:

* service matching
* closest package recommendation

---

## LangGraph Expansion

Add nodes:

```text id="o6t2n0"
load_services_node
recommend_service_node
show_services_node
service_selection_node
```

---

## Important

This phase should support:

### Test Case 3

Service not found.

You need:

* similarity matching
* fallback recommendation

Example:

```text id="4qfjhc"
Large Husky not found
→ suggest closest large dog package
```

---

# Phase 4 — Booking Workflow

## Goal

Implement booking FSM.

This is where LangGraph becomes VERY useful.

---

# Required Flow

```text id="ql5fng"
show_business_hours
    ↓
ask_booking_day
    ↓
validate_day
    ↓
fetch_available_slots
    ↓
show_slots
    ↓
ask_time_selection
    ↓
validate_slot
    ↓
create_calendar_event
    ↓
save_appointment
    ↓
confirm_booking
```

---

# Features

### Read BrandConfig

* business hours
* days

### Check Google Calendar

* slot conflicts
* availability

### Save booking

* Appointments sheet
* Google Calendar

### Update lead:

```text id="5t4t9n"
qualified → booked
```

---

# Critical Acceptance Requirement

Booking is ONLY valid if BOTH succeed:

```text id="88pb1v"
Google Calendar success
AND
Appointments sheet success
```

So you need transactional logic.

---

# Phase 5 — Generic Q&A / Business Information

## Goal

Handle informational queries.

---

## Questions like:

* location
* timings
* contact
* policies

---

## Data Source

Must come from:

```text id="m0n0pi"
BrandConfig sheet
```

NOT prompts.

---

## Add Intent Router

New router:

```text id="mvml2d"
intent_router
```

Routes:

```text id="fj8ol8"
booking
qualification
faq
pricing
objection
```

---

# Phase 6 — Objection Handling

## Goal

Handle pricing hesitation naturally.

Supports:

### Test Case 4

---

## Example

Customer:

```text id="1o4epw"
Too expensive
```

Bot:

* explains value
* suggests smaller package
* offers alternative

---

## Add Nodes

```text id="wv51qo"
objection_detection_node
objection_response_node
```

---

# Phase 7 — Follow-Up System

## Goal

Reminder automation.

Supports:

### Test Case 5

---

## Features

If lead:

```text id="t53v2f"
qualified but not booked
```

Then:

* schedule reminder
* send DM after 24–48h

---

## Add Components

### Reminder scheduler

Could use:

* asyncio task
* APScheduler
* Celery

---

## LangGraph Nodes

```text id="c6ovxl"
schedule_followup_node
send_followup_node
```

---

# Phase 8 — Error Recovery & Reliability

## Goal

Production-grade robustness.

---

## Handle:

* invalid time
* slot conflict
* Google API failure
* malformed LLM JSON
* missing services
* duplicate bookings

---

## Add:

* retry logic
* fallback paths
* validation layer

---

# Phase 9 — Evals & Testing

## Goal

Pass all acceptance criteria automatically.

VERY IMPORTANT.

---

# Create Automated Evals

For all 5 cases.

---

## Example Eval Structure

```text id="v1u8g9"
evals/
├── test_standard_booking.py
├── test_missing_info.py
├── test_service_not_found.py
├── test_objection.py
├── test_followup.py
```

---

# Validate:

* state transitions
* outputs
* booking creation
* reminders
* service matching

---

# Phase 10 — Refactor Into Production Architecture

After everything works.

---

# Final Architecture

```text id="qg38y3"
Discord
    ↓
LangGraph FSM
    ↓
Nodes
    ↓
Services Layer
    ├── Google Sheets
    ├── Calendar
    ├── Reminders
    └── Gemini
```

---

# Recommended Development Order

DO NOT build randomly.

Use this exact order:

```text id="9tbjlwm"
1. Foundation
2. Qualification
3. Services
4. Booking
5. FAQ
6. Objections
7. Followups
8. Reliability
9. Evals
10. Refactor
```

---

# Important Architectural Advice

## Keep This Separation STRICT

| Layer     | Responsibility       |
| --------- | -------------------- |
| LangGraph | workflow             |
| LLM       | extraction/reasoning |
| Services  | external APIs        |
| Storage   | persistence          |
| Discord   | transport            |
| Routers   | decisions            |
| Nodes     | business actions     |

This is the architecture interviewers and senior engineers expect.

---

# Your LangGraph FSM Will Eventually Look Like This

```text id="sd4im6"
START
  ↓
intent_router
  ├── qualification_flow
  ├── faq_flow
  ├── objection_flow
  └── booking_flow

qualification_flow
  ↓
qualified

booking_flow
  ↓
calendar_check
  ↓
appointment_creation
  ↓
booked

followup_flow
  ↓
reminder_sent
```

This is now a real AI workflow system, not just a chatbot.
