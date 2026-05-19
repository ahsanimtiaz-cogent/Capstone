from graph.state import GroomingState
from graph.nodes.session import PET_FIELDS
from services.sheets_service import is_valid_phone


def _missing_fields(session) -> list:
    missing = []
    if not session.get("phone") or not is_valid_phone(session.get("phone", "")):
        missing.append("phone")
    pet = session.get("pet", {}) or {}
    for f in PET_FIELDS:
        if not pet.get(f):
            missing.append(f"pet {f}")
    return missing


def ask_missing_fields_node(state: GroomingState):
    session = state.get("session", {})
    missing = _missing_fields(session)
    if state.get("reply") and missing:
        # the extraction node already composed a tailored ask
        return {"qualified": False, "reply": state["reply"]}

    if not missing:
        return {"qualified": False, "reply": "Looks like I have everything — let me confirm."}

    missing_str = ", ".join(missing)
    return {
        "qualified": False,
        "reply": (
            "To get you a quote, could you share: "
            f"{missing_str}? (For pet weight please include the unit, e.g. '12 kg'.)"
        ),
    }
