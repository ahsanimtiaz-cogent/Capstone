import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure the lang-graph package directory is on sys.path so `from graph...` works.
_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from dotenv import load_dotenv

from bot.discord_client import build_client
from bot.handlers import attach_handlers
from graph.workflow import build_graph
from services.calendar_service import CalendarService
from services.llm_service import LLMService
from services.reminder_service import ReminderService
from services.sheets_service import SheetsRepo


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def main() -> None:
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    discord_token = _require_env("DISCORD_TOKEN")
    gemini_key = _require_env("GEMINI_API_KEY")
    sheet_id = _require_env("GOOGLE_SHEET_ID")
    service_account_file = _require_env("GOOGLE_SERVICE_ACCOUNT_FILE")
    calendar_id = _require_env("GOOGLE_CALENDAR_ID")

    sessions_path = str(_HERE / "storage" / "sessions.json")
    followups_path = str(_HERE / "storage" / "followups.json")

    llm = LLMService(api_key=gemini_key)
    sheets = SheetsRepo(sheet_id=sheet_id, service_account_file=service_account_file)
    calendar = CalendarService(calendar_id=calendar_id)

    client = build_client()

    # The reminder service needs a way to DM users via the live client,
    # so we wire `send_dm` after handlers are attached.
    placeholder_send = lambda *a, **k: asyncio.sleep(0)  # type: ignore
    reminder = ReminderService(store_path=followups_path, send_fn=placeholder_send)

    graph = build_graph(sheets=sheets, calendar=calendar, llm=llm, reminder=reminder)
    send_dm = attach_handlers(client, graph, sheets, sessions_path)

    # Rebind reminder's send function to the real one and start.
    reminder._send_fn = send_dm  # noqa: SLF001
    # The scheduler must start inside the Discord event loop, so register a setup hook.

    @client.event
    async def setup_hook():  # type: ignore[override]
        reminder.start()

    client.run(discord_token)


if __name__ == "__main__":
    main()
