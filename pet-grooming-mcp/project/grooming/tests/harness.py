"""Eval harness — drives the Coordinator against in-memory Sheets/Calendar fakes."""
from typing import List, Tuple

from mcp_servers import mcp_utils

from project.grooming.orchestrator.coordinator import Coordinator

from .fakes import FakeCalendarService, FakeSheetsRepo


def install_fakes() -> Tuple[FakeSheetsRepo, FakeCalendarService]:
    sheets = FakeSheetsRepo()
    calendar = FakeCalendarService()
    mcp_utils.set_test_integrations(sheets=sheets, calendar=calendar)
    return sheets, calendar


class ConversationRunner:
    """Drives a conversation against the Coordinator, the same way the bot does."""

    def __init__(self, sheets: FakeSheetsRepo, user_id: str = "u1",
                 display_name: str = "Test User"):
        self.sheets = sheets
        self.user_id = user_id
        self.display_name = display_name
        self.history: List[dict] = []
        self.coordinator = Coordinator(sheets=sheets)

    def send(self, message: str) -> str:
        reply = self.coordinator.handle_message(self.user_id, message, self.display_name)
        self.history.append({"user": message, "bot": reply})
        return reply

    @property
    def session(self) -> dict:
        from project.grooming.models import ChatSession
        try:
            return dict(ChatSession.objects.get(discord_user_id=self.user_id).payload)
        except ChatSession.DoesNotExist:
            return {}
