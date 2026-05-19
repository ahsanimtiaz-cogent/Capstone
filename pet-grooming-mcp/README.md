# pet-grooming-mcp

MCP-based reimplementation of the LangGraph pet-grooming bot.

## Architecture

```
Discord  ──►  Coordinator (deterministic FSM, ported from LangGraph routers)
                │
                ├──► PydanticAI agents (intent, extraction, faq, objection) — OpenRouter
                │
                └──► MCPClient ──► Unified FastMCP server (port 8010)
                                       ├── qualification_mcp
                                       ├── services_mcp
                                       ├── booking_mcp
                                       ├── followup_mcp
                                       └── knowledge_mcp
                                              │
                                              └──► Google Sheets / Google Calendar
```

Persistence:
- **Postgres** (via Django models): `ChatSession`, `FollowupJob`, `MessageLog`
- **Google Sheets**: leads, services, appointments, brand config (unchanged from original)
- **Google Calendar**: slot search + event create/delete (unchanged from original)

Background jobs use **Celery + Celery Beat** in place of the original APScheduler.

## Quick start (local, without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.in
cp config/env/.env.example config/env/.env   # then edit values
python manage.py migrate

# Three processes (run in separate terminals):
make mcp        # FastMCP server on :8010
make bot        # Discord bot
celery -A project worker -l info
```

## Run with Docker

```bash
cp config/env/.env.example config/env/.env
make dev.build
make dev.up
```

## Tests

```bash
make test
```

Tests use in-memory fakes for Sheets/Calendar (ported from `lang-graph/evals/`).

## Mapping from the original LangGraph project

See [plan file](../.claude/plans/task-migrate-my-project-sorted-duckling.md) for the full node→tool mapping and migration notes.
