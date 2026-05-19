import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from graph.state import GroomingState, Stages
from services.calendar_service import CalendarService, is_valid_day
from services.sheets_service import SheetsRepo

logger = logging.getLogger(__name__)


_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_TIME_RE = re.compile(r"\b(\d{1,2}):?(\d{2})?\s*(am|pm)?\b", re.IGNORECASE)


def _extract_day(text: str) -> str:
    match = _DATE_RE.search(text or "")
    return match.group(1) if match else ""


def _normalise_time(text: str) -> str:
    """Pull a HH:MM string out of free text. Returns '' if not parseable."""
    match = _TIME_RE.search(text or "")
    if not match:
        return ""
    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    ampm = (match.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return ""


def _selected_service_or_error(state):
    selected = state.get("selected_service") or {}
    session = state.get("session", {})
    sid = selected.get("service_id") or session.get("selected_service_id")
    return sid, selected


def make_show_hours_and_ask_day_node(sheets: SheetsRepo):
    def node(state: GroomingState):
        brand = sheets.get_brand_config()
        session = dict(state.get("session", {}))
        session["stage"] = Stages.BOOKING_DAY
        return {
            "session": session,
            "reply": (
                f"We're open **{brand['hours']}** ({brand['timezone']}).\n"
                "Which day would you like to book? Please send a date in YYYY-MM-DD format."
            ),
        }
    return node


def make_fetch_and_show_slots_node(sheets: SheetsRepo, calendar: CalendarService):
    def node(state: GroomingState):
        session = dict(state.get("session", {}))
        brand = sheets.get_brand_config()

        day = _extract_day(state.get("user_message", "")) or session.get("booking_day", "")
        if not day:
            return {
                "reply": "Please send the date in YYYY-MM-DD format (e.g. 2026-05-22)."
            }

        ok, msg = is_valid_day(day, brand["hours"], brand["timezone"])
        if not ok:
            return {"reply": msg}

        sid, selected = _selected_service_or_error(state)
        if not sid or not selected.get("duration_min"):
            # Re-hydrate service info from session
            if session.get("selected_service_id"):
                svc = sheets.get_service(session["selected_service_id"])
                if svc:
                    selected = {
                        "service_id": svc["service_id"],
                        "title": svc["title"],
                        "duration_min": svc["duration_min"],
                        "base_price": svc["base_price"],
                    }
        if not selected.get("duration_min"):
            return {
                "reply": (
                    "Let's pick a service first — could you tell me which package you'd like?"
                )
            }

        slots = calendar.get_free_slots(
            day_str=day,
            duration_min=int(selected["duration_min"]),
            hours_str=brand["hours"],
            tz=brand["timezone"],
        )

        session["booking_day"] = day
        session["stage"] = Stages.BOOKING_SLOT

        if not slots:
            return {
                "session": session,
                "available_slots": [],
                "reply": (
                    f"Sorry — no {selected['duration_min']}-minute slots open on {day}. "
                    "Want to try another day?"
                ),
            }

        # Trim to the first ~6 to keep replies tidy.
        slots_to_show = slots[:6]
        lines = [
            f"{i+1}. {s['start_label']} – {s['end_label']}"
            for i, s in enumerate(slots_to_show)
        ]
        return {
            "session": session,
            "available_slots": slots,
            "selected_service": selected,
            "reply": (
                f"Here are available slots on {day} for **{selected.get('title','your service')}** "
                f"({selected['duration_min']} min):\n\n"
                + "\n".join(lines)
                + "\n\nReply with a start time (e.g. 11:00 or 2:30pm)."
            ),
        }
    return node


def make_book_appointment_node(sheets: SheetsRepo, calendar: CalendarService):
    """Validate slot → create Calendar event → save appointment → confirm. Transactional."""
    def node(state: GroomingState):
        session = dict(state.get("session", {}))
        brand = sheets.get_brand_config()
        tz = brand["timezone"]

        selected = state.get("selected_service") or {}
        sid = selected.get("service_id") or session.get("selected_service_id")
        if not sid:
            return {"reply": "We need to pick a service first."}

        if not selected.get("duration_min"):
            svc = sheets.get_service(sid)
            if svc:
                selected = {
                    "service_id": svc["service_id"],
                    "title": svc["title"],
                    "duration_min": svc["duration_min"],
                    "base_price": svc["base_price"],
                }
        duration_min = int(selected.get("duration_min") or 60)

        day = session.get("booking_day") or _extract_day(state.get("user_message", ""))
        if not day:
            return {"reply": "Which day would you like? (YYYY-MM-DD)"}

        user_time = _normalise_time(state.get("user_message", ""))
        if not user_time:
            return {
                "reply": (
                    "I didn't catch a time. Please reply with the start time, "
                    "e.g. 11:00 or 2:30pm."
                )
            }

        zone = ZoneInfo(tz)
        try:
            start_dt = datetime.strptime(f"{day} {user_time}", "%Y-%m-%d %H:%M").replace(tzinfo=zone)
        except ValueError:
            return {"reply": "That time didn't parse — try formats like 11:00 or 2:30pm."}

        end_dt = start_dt + timedelta(minutes=duration_min)
        start_iso = start_dt.isoformat()

        # Defense in depth 1: re-check the live calendar.
        if not calendar.is_slot_free(start_iso, duration_min, tz):
            # Re-fetch fresh slots so the user can pick again.
            fresh = calendar.get_free_slots(day, duration_min, brand["hours"], tz)
            session["stage"] = Stages.BOOKING_SLOT
            if not fresh:
                return {
                    "session": session,
                    "available_slots": [],
                    "reply": (
                        "That slot just got taken and no others remain on this day. "
                        "Want to try another date?"
                    ),
                }
            lines = [f"{i+1}. {s['start_label']} – {s['end_label']}" for i, s in enumerate(fresh[:6])]
            return {
                "session": session,
                "available_slots": fresh,
                "reply": (
                    "That slot just got taken. Here are fresh options:\n\n"
                    + "\n".join(lines)
                    + "\n\nReply with a start time."
                ),
            }

        # Defense in depth 2: same-lead overlap check against APPOINTMENTS sheet.
        lead_id = session.get("lead_id")
        if lead_id:
            existing = sheets.list_appointments_for_lead(lead_id)
            for appt in existing:
                if appt.get("status") in ("cancelled", "no_show", "completed"):
                    continue
                appt_start = appt.get("scheduled_at_iso", "")
                if not appt_start:
                    continue
                try:
                    a_start = datetime.fromisoformat(appt_start)
                    a_svc = sheets.get_service(appt.get("service_id", ""))
                    a_dur = int((a_svc or {}).get("duration_min") or 60)
                    a_end = a_start + timedelta(minutes=a_dur)
                except Exception:
                    continue
                if not (end_dt <= a_start or start_dt >= a_end):
                    return {
                        "reply": (
                            f"You already have an appointment around that time "
                            f"({appt_start}). Want to pick a different slot?"
                        )
                    }

        # Transactional write: create event first, then append row. If row fails, delete event.
        pet_name = session.get("pet", {}).get("name") or "your pet"
        summary = f"{selected.get('title','Grooming')} — {pet_name}"
        description = (
            f"Lead: {lead_id or '(unknown)'}\n"
            f"Service: {selected.get('title','')}\n"
            f"Pet: {pet_name}"
        )

        event_id = None
        try:
            event_id = calendar.create_event(start_iso, duration_min, summary, description, tz)
        except Exception as e:
            logger.exception("Calendar create_event failed: %s", e)
            return {
                "reply": "I couldn't create the calendar event. Please try another time."
            }

        try:
            appt_id = sheets.append_appointment(
                lead_id=lead_id or "",
                service_id=sid,
                scheduled_at_iso=start_iso,
                calendar_event_id=event_id,
                status="booked",
            )
            if lead_id:
                sheets.set_lead_status(lead_id, "booked")
        except Exception as e:
            logger.exception("Appointment write failed; rolling back calendar event %s: %s",
                             event_id, e)
            calendar.delete_event(event_id)
            return {
                "reply": "Booking failed while saving the appointment. The calendar slot has been released — please try again."
            }

        session["stage"] = Stages.BOOKED
        session["followup_required"] = False

        return {
            "session": session,
            "booking_confirmed": True,
            "reply": (
                f"Booked! **{selected.get('title','Service')}** on {day} from "
                f"{start_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')} "
                f"({duration_min} min). Appointment ID: {appt_id}. See you then!"
            ),
        }
    return node
