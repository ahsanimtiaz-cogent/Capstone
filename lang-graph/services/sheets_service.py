import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)


SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

APPOINTMENTS_HEADER = [
    "appt_id",
    "lead_id",
    "service_id",
    "status",
    "scheduled_at_iso",
    "calendar_event_id",
]

_PHONE_RE = re.compile(r"^[+0-9][0-9]{6,14}$")


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:10].upper()}"


def _parse_json_cell(cell: str, default: Any) -> Any:
    if not cell or not cell.strip():
        return default
    try:
        return json.loads(cell)
    except json.JSONDecodeError:
        return default


def is_valid_phone(phone: str) -> bool:
    if not phone:
        return False
    cleaned = re.sub(r"[\s\-()]", "", phone)
    return bool(_PHONE_RE.match(cleaned))


class SheetsRepo:
    """Thin gspread wrapper exposing typed CRUD for the grooming sheets."""

    _BRAND_TTL_SECONDS = 300

    def __init__(self, sheet_id: str, service_account_file: str):
        creds = Credentials.from_service_account_file(service_account_file, scopes=SHEETS_SCOPES)
        client = gspread.authorize(creds)
        self._spreadsheet = client.open_by_key(sheet_id)

        self._leads = self._spreadsheet.worksheet("Leads")
        self._services = self._spreadsheet.worksheet("Services")
        self._pets = self._spreadsheet.worksheet("Pets")
        self._appointments = self._spreadsheet.worksheet("Appointments")
        self._brand_config = self._spreadsheet.worksheet("BrandConfig")

        self._brand_cache: Optional[Dict[str, Any]] = None
        self._brand_cached_at: float = 0.0

        self._verify_appointments_header()

    # ---- header verification ------------------------------------------------

    def _verify_appointments_header(self) -> None:
        header = self._appointments.row_values(1)
        missing = [c for c in APPOINTMENTS_HEADER if c not in header]
        if missing:
            raise RuntimeError(
                "Appointments sheet is missing required columns: "
                f"{missing}. Expected header to include: {APPOINTMENTS_HEADER}. "
                "Add these columns to the live Google Sheet before booking."
            )

    # ---- LEADS --------------------------------------------------------------

    def get_lead_by_discord_id(self, discord_user_id: str) -> Optional[Dict[str, Any]]:
        for row in self._leads.get_all_records():
            if str(row.get("discord_user_id")) == str(discord_user_id):
                return dict(row)
        return None

    def create_lead(self, discord_user_id: str, name: str = "", phone: str = "",
                    city: str = "", source: str = "discord") -> Dict[str, Any]:
        lead_id = _new_id("LEAD")
        created_at = datetime.utcnow().isoformat()
        row = [
            lead_id,
            created_at,
            source,
            str(discord_user_id),
            name,
            phone,
            city,
            "initiated",
        ]
        self._leads.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Lead created: %s for discord_user_id=%s", lead_id, discord_user_id)
        return {
            "lead_id": lead_id,
            "created_at_iso": created_at,
            "source": source,
            "discord_user_id": str(discord_user_id),
            "name": name,
            "phone": phone,
            "city": city,
            "status": "initiated",
        }

    def update_lead(self, lead_id: str, **fields: Any) -> None:
        cell = self._leads.find(lead_id)
        if not cell:
            raise ValueError(f"Lead not found: {lead_id}")
        header = self._leads.row_values(1)
        for column, value in fields.items():
            if column not in header:
                continue
            col_idx = header.index(column) + 1
            self._leads.update_cell(cell.row, col_idx, value)

    def set_lead_status(self, lead_id: str, status: str) -> None:
        self.update_lead(lead_id, status=status)

    # ---- PETS ---------------------------------------------------------------

    def append_pet(self, lead_id: str, pet: Dict[str, Any]) -> str:
        pet_id = _new_id("PET")
        row = [
            lead_id,
            pet_id,
            pet.get("name", ""),
            pet.get("species", "dog"),
            pet.get("breed", ""),
            pet.get("weight", ""),
            pet.get("age", ""),
            pet.get("coat", ""),
            pet.get("notes", ""),
        ]
        self._pets.append_row(row, value_input_option="USER_ENTERED")
        return pet_id

    def list_pets_for_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._pets.get_all_records() if r.get("lead_id") == lead_id]

    # ---- SERVICES -----------------------------------------------------------

    def list_services(self) -> List[Dict[str, Any]]:
        out = []
        for row in self._services.get_all_records():
            out.append({
                "service_id": row.get("service_id", ""),
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "base_price": float(row.get("base_price", 0) or 0),
                "duration_min": int(row.get("duration_min", 0) or 0),
                "breed_modifier_json": _parse_json_cell(row.get("breed_modifier_json", ""), {}),
                "weight_brackets_json": _parse_json_cell(row.get("weight_brackets_json", ""), []),
                "upsells_json": _parse_json_cell(row.get("upsells_json", ""), []),
            })
        return out

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        for svc in self.list_services():
            if svc["service_id"] == service_id:
                return svc
        return None

    # ---- APPOINTMENTS -------------------------------------------------------

    def list_appointments_for_lead(self, lead_id: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._appointments.get_all_records()
                if r.get("lead_id") == lead_id]

    def append_appointment(self, lead_id: str, service_id: str,
                           scheduled_at_iso: str, calendar_event_id: str,
                           status: str = "booked") -> str:
        appt_id = _new_id("APPT")
        row = [appt_id, lead_id, service_id, status, scheduled_at_iso, calendar_event_id]
        self._appointments.append_row(row, value_input_option="USER_ENTERED")
        return appt_id

    # ---- BRAND CONFIG -------------------------------------------------------

    def get_brand_config(self, force_refresh: bool = False) -> Dict[str, Any]:
        now = time.time()
        if (not force_refresh
                and self._brand_cache is not None
                and (now - self._brand_cached_at) < self._BRAND_TTL_SECONDS):
            return self._brand_cache

        records = self._brand_config.get_all_records()
        if not records:
            raise RuntimeError("BrandConfig sheet is empty")
        row = records[0]
        config = {
            "brand_id": row.get("brand_id", ""),
            "brand_name": row.get("brand_name", ""),
            "welcome_copy": row.get("welcome_copy", ""),
            "hours": row.get("hours", ""),
            "location": row.get("location", ""),
            "timezone": row.get("timezone", "UTC"),
            "upsells_json": _parse_json_cell(row.get("upsells_json", ""), []),
            "objection_snippets_json": _parse_json_cell(row.get("objection_snippets_json", ""), {}),
        }
        self._brand_cache = config
        self._brand_cached_at = now
        return config
