"""In-memory fakes for SheetsRepo, CalendarService, LLMService, ReminderService.

Used by the eval harness so tests run offline, deterministically, and quickly.
"""
import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from evals.fixtures import BRAND_CONFIG, SERVICES


class FakeSheetsRepo:
    def __init__(self):
        self.leads: List[Dict[str, Any]] = []
        self.pets: List[Dict[str, Any]] = []
        self.appointments: List[Dict[str, Any]] = []
        self.fail_appointment_write: bool = False  # toggled in Phase 4 rollback test

    # ---- leads ---------------------------------------------------------
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

    # ---- pets ----------------------------------------------------------
    def append_pet(self, lead_id: str, pet: Dict[str, Any]) -> str:
        pet_id = f"PET{uuid.uuid4().hex[:6].upper()}"
        row = {
            "lead_id": lead_id,
            "pet_id": pet_id,
            "pet_name": pet.get("name", ""),
            "species": pet.get("species", "dog"),
            "breed": pet.get("breed", ""),
            "weight_kg": pet.get("weight", ""),
            "age_years": pet.get("age", ""),
            "coat_condition": pet.get("coat", ""),
            "notes": pet.get("notes", ""),
        }
        self.pets.append(row)
        return pet_id

    def list_pets_for_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        return [dict(p) for p in self.pets if p["lead_id"] == lead_id]

    # ---- services ------------------------------------------------------
    def list_services(self) -> List[Dict[str, Any]]:
        return [dict(s) for s in SERVICES]

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        for svc in SERVICES:
            if svc["service_id"] == service_id:
                return dict(svc)
        return None

    # ---- appointments --------------------------------------------------
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
            "lead_id": lead_id,
            "service_id": service_id,
            "status": status,
            "scheduled_at_iso": scheduled_at_iso,
            "calendar_event_id": calendar_event_id,
        })
        return appt_id

    # ---- brand ---------------------------------------------------------
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

    def add_busy_window(self, start_iso: str, duration_min: int) -> str:
        start = datetime.fromisoformat(start_iso)
        end = start + timedelta(minutes=duration_min)
        event_id = self._new_id()
        self.events.append({"id": event_id, "start": start, "end": end})
        return event_id

    def get_free_slots(self, day_str: str, duration_min: int,
                       hours_str: str, tz: str = "UTC") -> List[Dict[str, str]]:
        from services.calendar_service import parse_business_hours
        from zoneinfo import ZoneInfo

        parsed = parse_business_hours(hours_str)
        if parsed is None:
            return []
        zone = ZoneInfo(tz)
        day = datetime.strptime(day_str, "%Y-%m-%d")
        open_dt = datetime.combine(day.date(), parsed["open_time"]).replace(tzinfo=zone)
        close_dt = datetime.combine(day.date(), parsed["close_time"]).replace(tzinfo=zone)
        duration = timedelta(minutes=duration_min)

        # In tests we don't want "skip-the-past" filter to surprise us
        candidates: List[Dict[str, str]] = []
        step = timedelta(minutes=30)
        candidate = open_dt
        day_events = []
        for ev in self.events:
            ev_start = ev["start"].astimezone(zone) if ev["start"].tzinfo else ev["start"].replace(tzinfo=zone)
            ev_end = ev["end"].astimezone(zone) if ev["end"].tzinfo else ev["end"].replace(tzinfo=zone)
            if ev_start.date() == day.date():
                day_events.append((ev_start, ev_end))

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


class ScriptedLLM:
    """Deterministic LLM stub. Pattern-matches prompts and returns canned JSON/text."""

    def __init__(self):
        self.calls: List[str] = []
        self._extractors: List[Callable[[str], Optional[Dict[str, Any]]]] = []

    def _classify(self, prompt: str) -> str:
        if "Categories:" in prompt and "price" in prompt:
            return "objection_classify"
        if "Classify the user's objection" in prompt:
            return "objection_classify"
        if "Choose EXACTLY ONE intent" in prompt:
            return "intent"
        if "data extraction assistant" in prompt:
            return "extraction"
        if "answer questions about a dog grooming business" in prompt:
            return "faq"
        if "You handle an objection" in prompt:
            return "objection_response"
        return "other"

    def _user_message(self, prompt: str) -> str:
        m = re.search(r"USER MESSAGE:\s*\n?(.*?)(?:\n\nCURRENT SESSION|\n\n$|$)", prompt, re.DOTALL)
        if m:
            return m.group(1).strip()
        m2 = re.search(r"user's last message:\s*\n?\"([^\"]*)\"", prompt)
        if m2:
            return m2.group(1).strip()
        return ""

    def _session(self, prompt: str) -> Dict[str, Any]:
        m = re.search(r"CURRENT SESSION:\s*\n?(\{.*?\})\s*(?:USER MESSAGE|$)",
                      prompt, re.DOTALL)
        if not m:
            return {}
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return {}

    def _extract_from_message(self, msg: str, session: Dict[str, Any]) -> Dict[str, Any]:
        m = msg.lower()
        data: Dict[str, Any] = {
            "name": "",
            "phone": "",
            "note": "",
            "pet": {"name": "", "breed": "", "weight": "", "age": "", "coat": ""},
        }

        phone = re.search(r"(\+?\d[\d\- ]{6,}\d)", msg)
        if phone:
            data["phone"] = re.sub(r"[\s\-]", "", phone.group(1))

        breed_match = re.search(
            r"\b(husky|poodle|shih tzu|german shepherd|labrador|bulldog|mixed|maltese)\b",
            m,
        )
        if breed_match:
            data["pet"]["breed"] = breed_match.group(1).title()

        weight_match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|lbs?)", m)
        if weight_match:
            data["pet"]["weight"] = f"{weight_match.group(1)} {weight_match.group(2)}"

        age_match = re.search(r"(\d+(?:\.\d+)?)\s*(year|years|yr|yrs|month|months|mo)", m)
        if age_match:
            data["pet"]["age"] = f"{age_match.group(1)} {age_match.group(2)}"

        coat_match = re.search(r"\b(matted|smooth|curly|heavy[_ -]?shed|mild[_ -]?shed|normal|rough)\b", m)
        if coat_match:
            data["pet"]["coat"] = coat_match.group(1).replace(" ", "_").replace("-", "_")

        # Pet name candidates (try several patterns in order)
        breed_text = breed_match.group(1).lower() if breed_match else ""
        stopwords = {breed_text, "grooming", "the", "her", "his", "i", "a"}
        name_patterns = [
            r"\b(?:dog|pet|pup|cat)\s+(?:named|called)\s+([A-Z][a-z]+)",
            r"\bmy\s+(?:dog|pet|pup)\s+([A-Z][a-zA-Z]+)\b",
            r"\bfor\s+(?:my\s+(?:dog|pet|pup)\s+)?([A-Z][a-zA-Z]+)\b",
            r"\b(?:dog|pet|pup|cat)\s+([A-Z][a-zA-Z]+)\b",
            r"\b(?:her|his|its)?\s*name\s+is\s+([A-Z][a-zA-Z]+)",
        ]
        for pat in name_patterns:
            m_name = re.search(pat, msg)
            if m_name:
                candidate = m_name.group(1)
                if candidate.lower() not in stopwords:
                    data["pet"]["name"] = candidate
                    break

        # Carry forward existing pet fields the session already has
        if session:
            for k in ("name", "phone"):
                if session.get(k) and not data.get(k):
                    data[k] = session[k]
            pet_existing = session.get("pet", {}) or {}
            for k in ("name", "breed", "weight", "age", "coat"):
                if pet_existing.get(k) and not data["pet"].get(k):
                    data["pet"][k] = pet_existing[k]
        return data

    def invoke(self, prompt: str) -> str:
        self.calls.append(prompt)
        kind = self._classify(prompt)
        if kind == "faq":
            brand = BRAND_CONFIG
            return (
                f"We're open {brand['hours']} at {brand['location']}. "
                f"Time zone: {brand['timezone']}."
            )
        if kind == "objection_response":
            return (
                "Totally hear you — we keep pricing matched to coat and weight. "
                "Would a lighter Bath & Brush work instead?"
            )
        # Default plain text response
        return ""

    def invoke_json(self, prompt: str, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
        self.calls.append(prompt)
        kind = self._classify(prompt)
        msg = self._user_message(prompt)
        session = self._session(prompt)
        m = msg.lower()

        if kind == "intent":
            if any(w in m for w in ["too expensive", "expensive", "pricey", "think about"]):
                return {"intent": "objection"}
            if any(w in m for w in ["hours", "location", "where are you", "open", "address"]):
                return {"intent": "faq"}
            if any(w in m for w in ["book", "saturday", "tomorrow", "appointment", "available", "slot", "schedule"]):
                return {"intent": "booking"}
            if any(w in m for w in ["service", "price", "cost", "package", "options"]):
                return {"intent": "service_inquiry"}
            return {"intent": "qualification"}

        if kind == "extraction":
            data = self._extract_from_message(msg, session)
            missing = []
            if not data.get("phone"):
                missing.append("phone")
            for f in ("breed", "weight", "age", "coat"):
                if not data["pet"].get(f):
                    missing.append(f"pet {f}")
            message = "Got it!"
            if missing:
                message = "Could you share: " + ", ".join(missing) + "?"
            return {"data": data, "message": message}

        if kind == "objection_classify":
            if "expensive" in m or "pricey" in m or "discount" in m:
                return {"objection": "price"}
            if "think" in m or "later" in m:
                return {"objection": "hesitation"}
            return {"objection": "other"}

        return None


class FakeReminderService:
    def __init__(self):
        self.scheduled: List[Dict[str, Any]] = []

    def start(self) -> None:
        pass

    def schedule_followup(self, lead_id: str, discord_user_id: str,
                          message: str, delay_hours: float = 24.0) -> str:
        job_id = f"fu_{uuid.uuid4().hex[:6]}"
        send_at = datetime.utcnow() + timedelta(hours=delay_hours)
        self.scheduled.append({
            "job_id": job_id,
            "lead_id": lead_id,
            "discord_user_id": discord_user_id,
            "message": message,
            "send_at_iso": send_at.isoformat(),
        })
        return job_id

    def cancel_followup(self, job_id: str) -> None:
        self.scheduled = [j for j in self.scheduled if j["job_id"] != job_id]

    def list_pending(self) -> List[Dict[str, Any]]:
        return list(self.scheduled)
