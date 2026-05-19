"""In-memory fakes for SheetsRepo + CalendarService.

Ported from lang-graph/evals/fakes.py. Drop these into `mcp_servers.mcp_utils`
via `set_test_integrations` so the MCP tools (qualification, services,
booking, knowledge) read the fake data instead of hitting Google.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .fixtures import BRAND_CONFIG, SERVICES


class FakeSheetsRepo:
    def __init__(self):
        self.leads: List[Dict[str, Any]] = []
        self.pets: List[Dict[str, Any]] = []
        self.appointments: List[Dict[str, Any]] = []
        self.fail_appointment_write: bool = False

    def get_lead_by_discord_id(self, discord_user_id: str) -> Optional[Dict[str, Any]]:
        for lead in self.leads:
            if str(lead["discord_user_id"]) == str(discord_user_id):
                return dict(lead)
        return None

    def create_lead(self, discord_user_id: str, name: str = "", phone: str = "",
                    city: str = "", source: str = "discord") -> Dict[str, Any]:
        lead = {
            "lead_id": f"LEAD{uuid.uuid4().hex[:6].upper()}",
            "created_at_iso": datetime.utcnow().isoformat(),
            "source": source,
            "discord_user_id": str(discord_user_id),
            "name": name,
            "phone": phone,
            "city": city,
            "status": "initiated",
        }
        self.leads.append(lead)
        return dict(lead)

    def update_lead(self, lead_id: str, **fields: Any) -> None:
        for lead in self.leads:
            if lead["lead_id"] == lead_id:
                for k, v in fields.items():
                    if k in lead:
                        lead[k] = v
                return

    def set_lead_status(self, lead_id: str, status: str) -> None:
        self.update_lead(lead_id, status=status)

    def append_pet(self, lead_id: str, pet: Dict[str, Any]) -> str:
        pet_id = f"PET{uuid.uuid4().hex[:6].upper()}"
        row = {
            "lead_id": lead_id, "pet_id": pet_id,
            "pet_name": pet.get("name", ""), "species": pet.get("species", "dog"),
            "breed": pet.get("breed", ""), "weight_kg": pet.get("weight", ""),
            "age_years": pet.get("age", ""), "coat_condition": pet.get("coat", ""),
            "notes": pet.get("notes", ""),
        }
        self.pets.append(row)
        return pet_id

    def list_pets_for_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        return [dict(p) for p in self.pets if p["lead_id"] == lead_id]

    def list_services(self) -> List[Dict[str, Any]]:
        return [dict(s) for s in SERVICES]

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        for svc in SERVICES:
            if svc["service_id"] == service_id:
                return dict(svc)
        return None

    def list_appointments_for_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        return [dict(a) for a in self.appointments if a["lead_id"] == lead_id]

    def append_appointment(self, lead_id: str, service_id: str,
                           scheduled_at_iso: str, calendar_event_id: str,
                           status: str = "booked") -> str:
        if self.fail_appointment_write:
            raise RuntimeError("simulated sheet write failure")
        appt_id = f"APPT{uuid.uuid4().hex[:6].upper()}"
        self.appointments.append({
            "appt_id": appt_id,
            "lead_id": lead_id, "service_id": service_id,
            "status": status,
            "scheduled_at_iso": scheduled_at_iso,
            "calendar_event_id": calendar_event_id,
        })
        return appt_id

    def get_brand_config(self, force_refresh: bool = False) -> Dict[str, Any]:
        return dict(BRAND_CONFIG)


class FakeCalendarService:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.deleted: List[str] = []
        self._next_id = 0

    def _new_id(self) -> str:
        self._next_id += 1
        return f"ev_{self._next_id}"

    def get_free_slots(self, day_str: str, duration_min: int,
                       hours_str: str, tz: str = "UTC") -> List[Dict[str, str]]:
        from project.grooming.integrations.calendar_service import parse_business_hours
        from zoneinfo import ZoneInfo

        parsed = parse_business_hours(hours_str)
        if parsed is None:
            return []
        zone = ZoneInfo(tz)
        day = datetime.strptime(day_str, "%Y-%m-%d")
        open_dt = datetime.combine(day.date(), parsed["open_time"]).replace(tzinfo=zone)
        close_dt = datetime.combine(day.date(), parsed["close_time"]).replace(tzinfo=zone)
        duration = timedelta(minutes=duration_min)
        step = timedelta(minutes=30)

        day_events = []
        for ev in self.events:
            ev_start = ev["start"].astimezone(zone) if ev["start"].tzinfo else ev["start"].replace(tzinfo=zone)
            ev_end = ev["end"].astimezone(zone) if ev["end"].tzinfo else ev["end"].replace(tzinfo=zone)
            if ev_start.date() == day.date():
                day_events.append((ev_start, ev_end))

        candidates: List[Dict[str, str]] = []
        candidate = open_dt
        while candidate + duration <= close_dt:
            window_end = candidate + duration
            collides = any(not (window_end <= s or candidate >= e) for s, e in day_events)
            if not collides:
                candidates.append({
                    "start_iso": candidate.isoformat(),
                    "start_label": candidate.strftime("%H:%M"),
                    "end_label": window_end.strftime("%H:%M"),
                })
            candidate += step
        return candidates

    def is_slot_free(self, start_iso: str, duration_min: int, tz: str = "UTC") -> bool:
        from zoneinfo import ZoneInfo
        zone = ZoneInfo(tz)
        start = datetime.fromisoformat(start_iso).astimezone(zone)
        end = start + timedelta(minutes=duration_min)
        for ev in self.events:
            ev_start = ev["start"].astimezone(zone) if ev["start"].tzinfo else ev["start"].replace(tzinfo=zone)
            ev_end = ev["end"].astimezone(zone) if ev["end"].tzinfo else ev["end"].replace(tzinfo=zone)
            if not (end <= ev_start or start >= ev_end):
                return False
        return True

    def create_event(self, start_iso: str, duration_min: int,
                     summary: str, description: str = "", tz: str = "UTC") -> str:
        start = datetime.fromisoformat(start_iso)
        end = start + timedelta(minutes=duration_min)
        event_id = self._new_id()
        self.events.append({"id": event_id, "start": start, "end": end,
                           "summary": summary, "description": description})
        return event_id

    def delete_event(self, event_id: str) -> None:
        self.events = [e for e in self.events if e["id"] != event_id]
        self.deleted.append(event_id)
