from typing import Any, Dict

from graph.state import GroomingState, Stages
from services.sheets_service import SheetsRepo, is_valid_phone


PET_FIELDS = ("name", "breed", "weight", "age", "coat")


def _merge_pet(session: Dict[str, Any], pet: Dict[str, Any]) -> Dict[str, Any]:
    current = dict(session.get("pet", {}))
    for field in PET_FIELDS:
        value = pet.get(field)
        if value:
            current[field] = value
    session["pet"] = current
    return session


def _apply_extracted(session: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("name", "phone", "note"):
        value = extracted.get(key)
        if value:
            session[key] = value
    pet = extracted.get("pet") or {}
    if isinstance(pet, dict):
        _merge_pet(session, pet)
    return session


def is_qualified(session: Dict[str, Any]) -> bool:
    if not session.get("phone") or not is_valid_phone(session["phone"]):
        return False
    pet = session.get("pet", {}) or {}
    return all(pet.get(f) for f in PET_FIELDS)


def make_update_session_node(sheets: SheetsRepo):
    def update_session_node(state: GroomingState):
        session = dict(state.get("session", {}))
        session = _apply_extracted(session, state.get("extracted_data", {}) or {})

        if session.get("stage") == Stages.INITIATED and any(
            session.get("pet", {}).get(f) for f in PET_FIELDS
        ):
            session["stage"] = Stages.QUALIFYING

        lead_id = session.get("lead_id")
        if lead_id:
            updates: Dict[str, Any] = {}
            if session.get("name"):
                updates["name"] = session["name"]
            if session.get("phone"):
                updates["phone"] = session["phone"]
            if updates:
                try:
                    sheets.update_lead(lead_id, **updates)
                except Exception:
                    # non-fatal: we'll retry on the next turn
                    pass

        return {"session": session}

    return update_session_node
