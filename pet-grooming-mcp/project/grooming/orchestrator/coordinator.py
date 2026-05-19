"""Coordinator — the deterministic FSM that replaces lang-graph's compiled StateGraph.

`handle_message(user_id, text, display_name)`:
  1. Load (or create) the ChatSession row.
  2. Ensure a Sheets Leads row exists (or load the existing one).
  3. Call IntentAgent → intent (with stage-aware override, same logic as
     lang-graph/graph/nodes/intent.py).
  4. Dispatch via the ported routers; each branch calls one or more MCP tools.
  5. Persist the session + message log.

The branches mirror the original LangGraph node bodies, just rewritten to
read state from a plain dict and invoke MCP tools (in-process) instead of
returning a partial state for the graph to merge.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

from project.grooming.integrations.sheets_service import SheetsRepo
from project.grooming.mcp_client import MCPClient
from project.grooming.models import ChatSession, MessageLog

from .booking_router import booking_dispatch, service_inquiry_dispatch
from .intent_router import intent_router
from .session_service import (
    SessionService,
    apply_extracted,
    is_qualified,
    missing_field_prompt,
)
from .stages import Intents, PET_FIELDS, Stages

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_TIME_RE = re.compile(r"\b(\d{1,2}):?(\d{2})?\s*(am|pm)?\b", re.IGNORECASE)


def _extract_day(text: str) -> str:
    m = _DATE_RE.search(text or "")
    return m.group(1) if m else ""


def _normalise_time(text: str) -> str:
    m = _TIME_RE.search(text or "")
    if not m:
        return ""
    hour = int(m.group(1))
    minute = int(m.group(2) or "0")
    ampm = (m.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return ""


class Coordinator:
    """Holds the dependencies the FSM needs: an MCPClient and an optional SheetsRepo
    (for the leads lookup the bot does on first message)."""

    def __init__(self, mcp: Optional[MCPClient] = None, sheets: Optional[SheetsRepo] = None):
        # MCPClient is in-process; constructing it is free.
        self._mcp = mcp or MCPClient()
        # Sheets lead bootstrap stays in the bot's hot path (same as original).
        # If not injected, lazily resolve via mcp_servers.mcp_utils.get_sheets().
        self._sheets = sheets

    # --------------------------------------------------------------------
    # Dependency lookup helpers
    # --------------------------------------------------------------------

    def _get_sheets(self) -> SheetsRepo:
        if self._sheets is None:
            from mcp_servers.mcp_utils import get_sheets
            self._sheets = get_sheets()
        return self._sheets

    def _get_intent_agent(self):
        from project.grooming.agents.intent_agent import IntentAgent
        return IntentAgent()

    def _get_extraction_agent(self):
        from project.grooming.agents.extraction_agent import ExtractionAgent
        return ExtractionAgent()

    def _get_faq_agent(self):
        from project.grooming.agents.faq_agent import FaqAgent
        return FaqAgent()

    def _get_objection_agent(self):
        from project.grooming.agents.objection_agent import ObjectionAgent
        return ObjectionAgent()

    # --------------------------------------------------------------------
    # Public entry point
    # --------------------------------------------------------------------

    def handle_message(self, discord_user_id: str, text: str,
                       display_name: str = "") -> str:
        """Process one inbound user message; return the reply text."""
        row, session = SessionService.load(discord_user_id, display_name=display_name)
        session = self._bootstrap_lead(session, discord_user_id, display_name)

        stage_before = session.get("stage", "")
        intent_raw = self._get_intent_agent().classify(text, session)
        intent = self._stage_aware_intent(intent_raw, session)
        intent = intent_router(intent)

        ctx = {
            "_lead_id": session.get("lead_id") or "",
            "_discord_user_id": str(discord_user_id),
        }

        if intent == Intents.QUALIFICATION:
            reply, session = self._handle_qualification(text, session, ctx)
        elif intent == Intents.SERVICE_INQUIRY:
            reply, session = self._handle_service_inquiry(text, session, ctx)
        elif intent == Intents.BOOKING:
            reply, session = self._handle_booking(text, session, ctx)
        elif intent == Intents.FAQ:
            reply = self._handle_faq(text)
            # FAQ doesn't change session state
        elif intent == Intents.OBJECTION:
            reply, session = self._handle_objection(text, session, ctx)
        else:  # pragma: no cover - intent_router should have normalised this
            reply = "How can I help you with grooming today?"

        SessionService.save(row, session)
        MessageLog.objects.create(
            discord_user_id=str(discord_user_id),
            user_message=text,
            bot_reply=reply,
            intent=intent,
            stage_before=stage_before,
            stage_after=session.get("stage", ""),
        )
        return reply

    # --------------------------------------------------------------------
    # Lead bootstrap (replaces the inline logic in bot/handlers.py)
    # --------------------------------------------------------------------

    def _bootstrap_lead(self, session: Dict[str, Any], discord_user_id: str,
                        display_name: str) -> Dict[str, Any]:
        if session.get("lead_id"):
            return session
        sheets = self._get_sheets()
        try:
            existing = sheets.get_lead_by_discord_id(discord_user_id)
            if existing:
                session["lead_id"] = existing["lead_id"]
                session["name"] = existing.get("name") or session.get("name", "")
                session["phone"] = existing.get("phone") or session.get("phone", "")
                session["city"] = existing.get("city") or session.get("city", "")
            else:
                created = sheets.create_lead(
                    discord_user_id=discord_user_id, name=display_name or "",
                )
                session["lead_id"] = created["lead_id"]
        except Exception:
            logger.exception("Could not initialize lead for %s", discord_user_id)
        return session

    # --------------------------------------------------------------------
    # Intent post-processing (same rule as lang-graph/graph/nodes/intent.py)
    # --------------------------------------------------------------------

    def _stage_aware_intent(self, intent: str, session: Dict[str, Any]) -> str:
        stage = session.get("stage", Stages.INITIATED)
        # Trust strong opinions (anything except the default fallback).
        if intent in {Intents.SERVICE_INQUIRY, Intents.BOOKING,
                      Intents.FAQ, Intents.OBJECTION}:
            return intent
        # qualification fallback: adjust by stage
        if stage in (Stages.BOOKING_DAY, Stages.BOOKING_SLOT):
            return Intents.BOOKING
        if stage == Stages.SERVICE_SELECTION:
            return Intents.SERVICE_INQUIRY
        return Intents.QUALIFICATION

    # --------------------------------------------------------------------
    # Branch handlers
    # --------------------------------------------------------------------

    def _handle_qualification(self, text: str, session: Dict[str, Any],
                              ctx: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        extracted, extraction_reply = self._get_extraction_agent().extract(text, session)
        session = apply_extracted(session, extracted)
        session = SessionService.promote_stage_if_data_present(session)
        self._sync_contact_to_sheets(session)

        if is_qualified(session):
            return self._qualify_and_show_services(session, ctx)

        # Still missing — bot prompts for what's left.
        if extraction_reply:
            return extraction_reply, session
        return missing_field_prompt(session), session

    def _qualify_and_show_services(self, session: Dict[str, Any],
                                   ctx: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        ctx = {**ctx, "_lead_id": session.get("lead_id") or ""}
        pet = session.get("pet", {})
        self._mcp.qualify_lead(
            ctx,
            name=session.get("name", ""),
            phone=session.get("phone", ""),
            note=session.get("note", ""),
            pet=pet,
        )
        session["stage"] = Stages.QUALIFIED

        listing = self._mcp.list_services(ctx, pet=pet)
        if not listing.services:
            return ("You're all set! We're updating our service menu — I'll be back shortly.",
                    session)

        recommended_line = ""
        rec_id = listing.recommended_service_id
        if rec_id:
            rec = next((s for s in listing.services if s.service_id == rec_id), None)
            if rec:
                recommended_line = (
                    f"\n\nRecommended for {pet.get('name') or 'your pet'}: "
                    f"**{rec.title}** — ${rec.final_price:.2f} ({rec.duration_min} min)."
                )
                if rec.is_fallback and rec.fallback_reason:
                    recommended_line += f"\n_{rec.fallback_reason}_"

        session["recommended_service_id"] = rec_id
        session["stage"] = Stages.SERVICE_SELECTION
        session["selected_service_id"] = None

        reply = (
            "Great — you're qualified! Here's what we offer:\n\n"
            f"{listing.formatted_text}{recommended_line}\n\n"
            "Which one would you like, or want to know more about a specific service?"
        )
        return reply, session

    def _handle_service_inquiry(self, text: str, session: Dict[str, Any],
                                ctx: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        choice = service_inquiry_dispatch(session)
        if choice == "select_service":
            return self._select_service(text, session, ctx)
        return self._show_services(session, ctx)

    def _show_services(self, session: Dict[str, Any], ctx: Dict[str, Any]
                       ) -> Tuple[str, Dict[str, Any]]:
        pet = session.get("pet", {})
        listing = self._mcp.list_services(ctx, pet=pet)
        if not listing.services:
            return "Our service menu is being updated — please check back shortly.", session

        rec_line = ""
        rec_id = listing.recommended_service_id
        session["recommended_service_id"] = rec_id
        if rec_id:
            rec = next((s for s in listing.services if s.service_id == rec_id), None)
            if rec:
                rec_line = (
                    f"\n\nRecommended: **{rec.title}** — "
                    f"${rec.final_price:.2f} ({rec.duration_min} min)."
                )
                if rec.is_fallback and rec.fallback_reason:
                    rec_line += f"\n_{rec.fallback_reason}_"
        return "Here are our services:\n\n" + listing.formatted_text + rec_line, session

    def _select_service(self, text: str, session: Dict[str, Any], ctx: Dict[str, Any]
                        ) -> Tuple[str, Dict[str, Any]]:
        pet = session.get("pet", {})
        result = self._mcp.select_service(
            ctx,
            user_text=text,
            pet=pet,
            recommended_service_id=session.get("recommended_service_id") or "",
        )
        if not result.matched:
            listing = self._mcp.list_services(ctx, pet=pet)
            return (
                "I didn't catch which service you'd like. Here are the options again:\n\n"
                + listing.formatted_text
                + "\n\nWhich would you like?",
                session,
            )

        svc = result.selected
        session["selected_service_id"] = svc.service_id
        session["stage"] = Stages.BOOKING_DAY
        fb_note = (
            f"\n_{svc.fallback_reason}_" if svc.is_fallback and svc.fallback_reason else ""
        )
        reply = (
            f"Great choice — **{svc.title}** "
            f"(${svc.final_price:.2f}, {svc.duration_min} min).{fb_note}\n\n"
            "Which day works for you? Please send a date in YYYY-MM-DD format."
        )
        return reply, session

    def _handle_booking(self, text: str, session: Dict[str, Any], ctx: Dict[str, Any]
                        ) -> Tuple[str, Dict[str, Any]]:
        choice = booking_dispatch(session)
        if choice == "end":
            return "You're already booked — anything else?", session
        if choice == "extract":
            return self._handle_qualification(text, session, ctx)
        if choice == "show_services":
            return self._show_services(session, ctx)
        if choice == "select_service":
            return self._select_service(text, session, ctx)
        if choice == "show_hours":
            return self._show_hours_ask_day(session, ctx)
        if choice == "fetch_slots":
            return self._fetch_slots(text, session, ctx)
        if choice == "book":
            return self._book_slot(text, session, ctx)
        return "Let me get you set up — what would you like to book?", session

    def _show_hours_ask_day(self, session: Dict[str, Any], ctx: Dict[str, Any]
                            ) -> Tuple[str, Dict[str, Any]]:
        hours = self._mcp.show_hours(ctx)
        session["stage"] = Stages.BOOKING_DAY
        reply = (
            f"We're open **{hours.hours}** ({hours.timezone}).\n"
            "Which day would you like to book? Please send a date in YYYY-MM-DD format."
        )
        return reply, session

    def _fetch_slots(self, text: str, session: Dict[str, Any], ctx: Dict[str, Any]
                     ) -> Tuple[str, Dict[str, Any]]:
        day = _extract_day(text) or session.get("booking_day", "")
        if not day:
            return "Please send the date in YYYY-MM-DD format (e.g. 2026-05-22).", session

        service_id = session.get("selected_service_id") or ""
        if not service_id:
            return (
                "Let's pick a service first — could you tell me which package you'd like?",
                session,
            )

        result = self._mcp.fetch_free_slots(ctx, day=day, service_id=service_id)
        if result.error:
            return result.error, session

        session["booking_day"] = day
        session["stage"] = Stages.BOOKING_SLOT

        if not result.slots:
            return (
                f"Sorry — no {result.duration_min}-minute slots open on {day}. "
                "Want to try another day?",
                session,
            )

        slots_to_show = result.slots[:6]
        lines = [f"{i+1}. {s.start_label} – {s.end_label}"
                 for i, s in enumerate(slots_to_show)]
        sheets = self._get_sheets()
        svc = sheets.get_service(service_id)
        title = (svc or {}).get("title", "your service")
        reply = (
            f"Here are available slots on {day} for **{title}** "
            f"({result.duration_min} min):\n\n"
            + "\n".join(lines)
            + "\n\nReply with a start time (e.g. 11:00 or 2:30pm)."
        )
        return reply, session

    def _book_slot(self, text: str, session: Dict[str, Any], ctx: Dict[str, Any]
                   ) -> Tuple[str, Dict[str, Any]]:
        service_id = session.get("selected_service_id") or ""
        if not service_id:
            return "We need to pick a service first.", session

        day = session.get("booking_day") or _extract_day(text)
        if not day:
            return "Which day would you like? (YYYY-MM-DD)", session

        start_time = _normalise_time(text)
        if not start_time:
            return (
                "I didn't catch a time. Please reply with the start time, "
                "e.g. 11:00 or 2:30pm.",
                session,
            )

        pet_name = session.get("pet", {}).get("name") or "your pet"
        result = self._mcp.book_appointment(
            ctx, day=day, start_time=start_time,
            service_id=service_id, pet_name=pet_name,
        )

        if not result.booked:
            if result.error == "slot_taken" and result.conflict_replacement_slots:
                lines = [
                    f"{i+1}. {s.start_label} – {s.end_label}"
                    for i, s in enumerate(result.conflict_replacement_slots[:6])
                ]
                return (
                    "That slot just got taken. Here are fresh options:\n\n"
                    + "\n".join(lines)
                    + "\n\nReply with a start time.",
                    session,
                )
            if result.error == "slot_taken":
                return (
                    "That slot just got taken and no others remain on this day. "
                    "Want to try another date?",
                    session,
                )
            return (result.error or "Booking failed — please try another time."), session

        session["stage"] = Stages.BOOKED
        session["followup_required"] = False

        # Derive end label for the confirmation message
        sheets = self._get_sheets()
        brand = sheets.get_brand_config()
        tz = ZoneInfo(brand.get("timezone", "UTC"))
        start_dt = datetime.fromisoformat(result.scheduled_at_iso).astimezone(tz)
        end_dt = start_dt + timedelta(minutes=result.duration_min or 0)
        svc = sheets.get_service(service_id) or {}
        title = svc.get("title", "Service")
        reply = (
            f"Booked! **{title}** on {day} from "
            f"{start_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')} "
            f"({result.duration_min} min). Appointment ID: {result.appt_id}. See you then!"
        )
        return reply, session

    # --------------------------------------------------------------------
    # FAQ + Objection
    # --------------------------------------------------------------------

    def _handle_faq(self, text: str) -> str:
        ctx: Dict[str, Any] = {}
        brand = self._mcp.get_brand_config(ctx)
        return self._get_faq_agent().answer(
            user_message=text,
            brand_name=brand.brand_name or "Paws & Relax",
            hours=brand.hours,
            location=brand.location,
            timezone=brand.timezone,
        )

    def _handle_objection(self, text: str, session: Dict[str, Any], ctx: Dict[str, Any]
                          ) -> Tuple[str, Dict[str, Any]]:
        brand = self._mcp.get_brand_config(ctx)
        snippets = brand.objection_snippets or {}
        selected_id = session.get("selected_service_id") or ""
        service_summary = "(no service selected yet)"
        if selected_id:
            sheets = self._get_sheets()
            svc = sheets.get_service(selected_id)
            if svc:
                service_summary = f"{svc['title']} — ${svc.get('base_price', 0):.2f}"

        reply = self._get_objection_agent().respond(
            user_message=text,
            brand_name=brand.brand_name or "Paws & Relax",
            objection_snippets=snippets,
            service_summary=service_summary,
        )

        session["followup_required"] = True

        # Schedule a follow-up DM (idempotent per lead).
        try:
            self._mcp.schedule_followup(
                ctx,
                message=(
                    "Hi! Just checking back about your grooming appointment. "
                    "Want me to find a time that works for you?"
                ),
                delay_hours=24.0,
            )
        except Exception as e:
            logger.warning("schedule_followup failed: %s", e)

        # Flip lead status to follow_up (mirrors lang-graph followup_node).
        lead_id = session.get("lead_id")
        if lead_id and session.get("stage") != Stages.BOOKED:
            try:
                self._get_sheets().set_lead_status(lead_id, "follow_up")
            except Exception:
                pass

        suffix = "\n\nI'll check back with you in a day or so — no pressure!"
        return (reply + suffix) if reply else suffix.lstrip(), session

    # --------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------

    def _sync_contact_to_sheets(self, session: Dict[str, Any]) -> None:
        lead_id = session.get("lead_id")
        if not lead_id:
            return
        updates: Dict[str, Any] = {}
        if session.get("name"):
            updates["name"] = session["name"]
        if session.get("phone"):
            updates["phone"] = session["phone"]
        if not updates:
            return
        try:
            self._get_sheets().update_lead(lead_id, **updates)
        except Exception:
            # Non-fatal: retried implicitly on the next turn.
            pass
