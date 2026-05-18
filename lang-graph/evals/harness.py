"""Eval harness: drive a scripted multi-turn conversation against the graph with fakes."""
from typing import Any, Dict, List, Optional, Tuple

from graph.state import GroomingState, empty_session
from graph.workflow import build_graph

from evals.fakes import FakeSheetsRepo, FakeCalendarService, FakeReminderService, ScriptedLLM


def make_runtime(sheets: Optional[FakeSheetsRepo] = None,
                 calendar: Optional[FakeCalendarService] = None,
                 llm: Optional[ScriptedLLM] = None,
                 reminder: Optional[FakeReminderService] = None
                 ) -> Tuple[Any, FakeSheetsRepo, FakeCalendarService, ScriptedLLM, FakeReminderService]:
    sheets = sheets or FakeSheetsRepo()
    calendar = calendar or FakeCalendarService()
    llm = llm or ScriptedLLM()
    reminder = reminder or FakeReminderService()
    graph = build_graph(sheets=sheets, calendar=calendar, llm=llm, reminder=reminder)
    return graph, sheets, calendar, llm, reminder


class ConversationRunner:
    """Drives a conversation against the compiled graph. Persists session
    between turns the way bot.handlers does."""

    def __init__(self, graph, sheets: FakeSheetsRepo, user_id: str = "u1",
                 display_name: str = "Test User"):
        self.graph = graph
        self.sheets = sheets
        self.user_id = user_id
        self.display_name = display_name
        self.session: Dict[str, Any] = empty_session()
        self.history: List[Dict[str, str]] = []
        self.last_state: GroomingState = {}

    def send(self, message: str) -> str:
        # Initialize lead the way bot.handlers does.
        if not self.session.get("lead_id"):
            existing = self.sheets.get_lead_by_discord_id(self.user_id)
            if existing:
                self.session["lead_id"] = existing["lead_id"]
            else:
                created = self.sheets.create_lead(self.user_id, name=self.display_name)
                self.session["lead_id"] = created["lead_id"]

        state: GroomingState = {
            "user_id": self.user_id,
            "user_message": message,
            "session": self.session,
            "intent": "",
            "extracted_data": {},
            "selected_service": {},
            "available_slots": [],
            "booking_day": self.session.get("booking_day", ""),
            "booking_time": "",
            "booking_confirmed": False,
            "qualified": False,
            "reply": "",
            "errors": [],
        }
        result: GroomingState = self.graph.invoke(state)
        self.session = result.get("session", self.session)
        self.last_state = result
        reply = result.get("reply") or ""
        self.history.append({"user": message, "bot": reply})
        return reply
