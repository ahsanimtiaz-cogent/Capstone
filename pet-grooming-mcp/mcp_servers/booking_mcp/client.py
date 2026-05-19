"""Booking business logic: ported from lang-graph/graph/nodes/booking.py.

Preserves transactional behavior: Calendar event is created first, then
the Appointments sheet row is appended; on sheet failure, the calendar
event is deleted (rollback). Same-lead overlap check is preserved.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from project.grooming.integrations.calendar_service import is_valid_day

from ..base_client import BaseMCPClient
from ..mcp_utils import get_calendar, get_sheets
from .models import (
    BookAppointmentRequest,
    BookAppointmentResponse,
    FetchFreeSlotsRequest,
    FetchFreeSlotsResponse,
    FreeSlot,
    ShowHoursRequest,
    ShowHoursResponse,
)


def _parse_start_dt(day: str, start_time: str, tz: str) -> datetime:
    return datetime.strptime(f"{day} {start_time}", "%Y-%m-%d %H:%M").replace(
        tzinfo=ZoneInfo(tz)
    )


class BookingMCPClient(BaseMCPClient):

    def show_hours(self, _request: ShowHoursRequest) -> ShowHoursResponse:
        brand = get_sheets().get_brand_config()
        return ShowHoursResponse(
            hours=brand.get("hours", ""),
            timezone=brand.get("timezone", "UTC"),
        )

    def fetch_free_slots(self, request: FetchFreeSlotsRequest) -> FetchFreeSlotsResponse:
        sheets = get_sheets()
        calendar = get_calendar()
        brand = sheets.get_brand_config()

        ok, msg = is_valid_day(request.day, brand["hours"], brand["timezone"])
        if not ok:
            return FetchFreeSlotsResponse(
                day=request.day, duration_min=0, slots=[], error=msg
            )

        svc = sheets.get_service(request.service_id)
        if not svc:
            return FetchFreeSlotsResponse(
                day=request.day, duration_min=0, slots=[],
                error=f"Unknown service: {request.service_id}",
            )
        duration_min = int(svc["duration_min"])

        raw_slots = calendar.get_free_slots(
            day_str=request.day,
            duration_min=duration_min,
            hours_str=brand["hours"],
            tz=brand["timezone"],
        )
        return FetchFreeSlotsResponse(
            day=request.day,
            duration_min=duration_min,
            slots=[FreeSlot(**s) for s in raw_slots],
        )

    def book_appointment(self, request: BookAppointmentRequest) -> BookAppointmentResponse:
        sheets = get_sheets()
        calendar = get_calendar()
        brand = sheets.get_brand_config()
        tz = brand["timezone"]

        svc = sheets.get_service(request.service_id)
        if not svc:
            return BookAppointmentResponse(
                booked=False, error=f"Unknown service: {request.service_id}"
            )
        duration_min = int(svc["duration_min"])
        title = svc["title"]

        try:
            start_dt = _parse_start_dt(request.day, request.start_time, tz)
        except ValueError:
            return BookAppointmentResponse(
                booked=False,
                error="That time didn't parse — try formats like 11:00 or 14:30.",
            )
        end_dt = start_dt + timedelta(minutes=duration_min)
        start_iso = start_dt.isoformat()

        # Defense in depth 1: re-check the live calendar.
        if not calendar.is_slot_free(start_iso, duration_min, tz):
            fresh = calendar.get_free_slots(request.day, duration_min, brand["hours"], tz)
            return BookAppointmentResponse(
                booked=False,
                error="slot_taken",
                conflict_replacement_slots=[FreeSlot(**s) for s in fresh[:6]],
            )

        # Defense in depth 2: same-lead overlap against Appointments sheet.
        if self.lead_id:
            existing = sheets.list_appointments_for_lead(self.lead_id)
            for appt in existing:
                if appt.get("status") in ("cancelled", "no_show", "completed"):
                    continue
                appt_start_iso = appt.get("scheduled_at_iso", "")
                if not appt_start_iso:
                    continue
                try:
                    a_start = datetime.fromisoformat(appt_start_iso)
                    a_svc = sheets.get_service(appt.get("service_id", ""))
                    a_dur = int((a_svc or {}).get("duration_min") or 60)
                    a_end = a_start + timedelta(minutes=a_dur)
                except Exception:
                    continue
                if not (end_dt <= a_start or start_dt >= a_end):
                    return BookAppointmentResponse(
                        booked=False,
                        error=f"You already have an appointment around {appt_start_iso}.",
                    )

        # Transactional write: Calendar first, then Sheet row; rollback on Sheet failure.
        summary = f"{title} — {request.pet_name or 'your pet'}"
        description = (
            f"Lead: {self.lead_id or '(unknown)'}\n"
            f"Service: {title}\n"
            f"Pet: {request.pet_name}"
        )

        try:
            event_id = calendar.create_event(start_iso, duration_min, summary, description, tz)
        except Exception as e:
            self.logger.exception("Calendar create_event failed: %s", e)
            return BookAppointmentResponse(
                booked=False, error="Could not create the calendar event."
            )

        try:
            appt_id = sheets.append_appointment(
                lead_id=self.lead_id or "",
                service_id=request.service_id,
                scheduled_at_iso=start_iso,
                calendar_event_id=event_id,
                status="booked",
            )
            if self.lead_id:
                sheets.set_lead_status(self.lead_id, "booked")
        except Exception as e:
            self.logger.exception(
                "Appointment write failed; rolling back calendar event %s: %s", event_id, e
            )
            calendar.delete_event(event_id)
            return BookAppointmentResponse(
                booked=False,
                error="Booking failed while saving the appointment. Calendar slot released.",
            )

        return BookAppointmentResponse(
            booked=True,
            appt_id=appt_id,
            calendar_event_id=event_id,
            scheduled_at_iso=start_iso,
            duration_min=duration_min,
        )
