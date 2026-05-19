import logging

from graph.state import GroomingState, Stages
from services.reminder_service import ReminderService
from services.sheets_service import SheetsRepo

logger = logging.getLogger(__name__)


def make_schedule_followup_node(sheets: SheetsRepo, reminder: ReminderService,
                                delay_hours: float = 24.0):
    def node(state: GroomingState):
        session = dict(state.get("session", {}))
        lead_id = session.get("lead_id")
        user_id = state.get("user_id")
        if not lead_id or not user_id:
            return {"reply": state.get("reply") or "No worries — take your time. I'm here when you're ready."}

        # Idempotency: avoid scheduling twice for the same lead.
        already = any(j.get("lead_id") == lead_id for j in reminder.list_pending())
        if not already:
            message = (
                "Hi! Just checking back about your grooming appointment. "
                "Want me to find a time that works for you?"
            )
            try:
                reminder.schedule_followup(
                    lead_id=lead_id,
                    discord_user_id=user_id,
                    message=message,
                    delay_hours=delay_hours,
                )
            except Exception as e:
                logger.warning("Could not schedule follow-up: %s", e)

        # Update lead status if still in qualified state
        if lead_id and session.get("stage") != Stages.BOOKED:
            try:
                sheets.set_lead_status(lead_id, "follow_up")
            except Exception:
                pass

        session["followup_required"] = True
        existing_reply = state.get("reply") or ""
        suffix = "\n\nI'll check back with you in a day or so — no pressure!"

        return {
            "session": session,
            "reply": (existing_reply + suffix) if existing_reply else suffix.lstrip(),
        }
    return node
