"""Shared MCP-server utilities: error handler + integration singletons.

The integration singletons (`get_sheets`, `get_calendar`) are lazy and cached
so the heavyweight Google clients are instantiated once per process — the
five domain clients share them.
"""
import logging
import os
import traceback
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


import inspect


async def handle_tool_call(api_call: Callable[[], Any]) -> Any:
    """Run a tool body (sync or async) and convert exceptions into a structured error."""
    try:
        result = api_call()
        if inspect.isawaitable(result):
            result = await result
        return result
    except Exception as e:
        logger.error("Error in handle_tool_call: %s\n%s", e, traceback.format_exc())
        return {"error": str(e)}


# ---- Integration singletons -------------------------------------------------
_sheets_singleton = None
_calendar_singleton = None


def get_sheets():
    """Return a process-wide SheetsRepo, instantiating on first call."""
    global _sheets_singleton
    if _sheets_singleton is None:
        from project.grooming.integrations.sheets_service import SheetsRepo
        sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
        sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
        if not sheet_id or not sa_file:
            raise RuntimeError(
                "GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_FILE must be set."
            )
        _sheets_singleton = SheetsRepo(sheet_id=sheet_id, service_account_file=sa_file)
    return _sheets_singleton


def get_calendar():
    """Return a process-wide CalendarService, instantiating on first call."""
    global _calendar_singleton
    if _calendar_singleton is None:
        from project.grooming.integrations.calendar_service import CalendarService
        calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
        creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        token_path = os.environ.get("GOOGLE_TOKEN_PATH", "token.pickle")
        _calendar_singleton = CalendarService(
            calendar_id=calendar_id,
            credentials_path=creds_path,
            token_path=token_path,
        )
    return _calendar_singleton


def set_test_integrations(sheets: Optional[Any] = None, calendar: Optional[Any] = None) -> None:
    """Inject fakes (used by tests so we don't hit Google in CI)."""
    global _sheets_singleton, _calendar_singleton
    if sheets is not None:
        _sheets_singleton = sheets
    if calendar is not None:
        _calendar_singleton = calendar
