"""Postgres-backed session CRUD + qualification helpers.

Replaces the per-process JSON file `lang-graph/storage/sessions.json` with
a Django `ChatSession` row. Functions mirror lang-graph/graph/nodes/session.py
and lang-graph/graph/nodes/ask_missing.py.
"""
from typing import Any, Dict, List, Tuple

from project.grooming.integrations.sheets_service import is_valid_phone
from project.grooming.models import ChatSession

from .stages import PET_FIELDS, Stages, empty_session


def _merge_pet(session: Dict[str, Any], pet: Dict[str, Any]) -> Dict[str, Any]:
    current = dict(session.get("pet", {}))
    for field in PET_FIELDS:
        value = pet.get(field)
        if value:
            current[field] = value
    session["pet"] = current
    return session


def apply_extracted(session: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Merge extracted customer/pet fields into the session (never overwriting with empty)."""
    for key in ("name", "phone", "note"):
        value = extracted.get(key)
        if value:
            session[key] = value
    pet = extracted.get("pet") or {}
    if isinstance(pet, dict):
        _merge_pet(session, pet)
    return session


def is_qualified(session: Dict[str, Any]) -> bool:
    if not session.get("phone") or not is_valid_phone(session.get("phone", "")):
        return False
    pet = session.get("pet", {}) or {}
    return all(pet.get(f) for f in PET_FIELDS)


def missing_fields(session: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    if not session.get("phone") or not is_valid_phone(session.get("phone", "")):
        missing.append("phone")
    pet = session.get("pet", {}) or {}
    for f in PET_FIELDS:
        if not pet.get(f):
            missing.append(f"pet {f}")
    return missing


def missing_field_prompt(session: Dict[str, Any]) -> str:
    fields = missing_fields(session)
    if not fields:
        return "Looks like I have everything — let me confirm."
    return (
        "To get you a quote, could you share: "
        f"{', '.join(fields)}? (For pet weight please include the unit, e.g. '12 kg'.)"
    )


# ---- Persistence ----------------------------------------------------------

class SessionService:
    """Load / save the per-Discord-user session row in Postgres."""

    @staticmethod
    def load(discord_user_id: str, display_name: str = "") -> Tuple[ChatSession, Dict[str, Any]]:
        row, created = ChatSession.objects.get_or_create(
            discord_user_id=str(discord_user_id),
            defaults={"display_name": display_name, "payload": empty_session()},
        )
        if not created and display_name and not row.display_name:
            row.display_name = display_name
            row.save(update_fields=["display_name"])
        return row, dict(row.payload or empty_session())

    @staticmethod
    def save(row: ChatSession, session: Dict[str, Any]) -> None:
        row.payload = session
        row.save(update_fields=["payload", "updated_at"])

    @staticmethod
    def promote_stage_if_data_present(session: Dict[str, Any]) -> Dict[str, Any]:
        if session.get("stage") == Stages.INITIATED and any(
            session.get("pet", {}).get(f) for f in PET_FIELDS
        ):
            session["stage"] = Stages.QUALIFYING
        return session
