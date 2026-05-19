from typing import TypedDict, Dict, Any, List


class Stages:
    INITIATED = "initiated"
    QUALIFYING = "qualifying"
    QUALIFIED = "qualified"
    SERVICE_SELECTION = "service_selection"
    BOOKING_DAY = "booking_day"
    BOOKING_SLOT = "booking_slot"
    BOOKED = "booked"


class Intents:
    QUALIFICATION = "qualification"
    SERVICE_INQUIRY = "service_inquiry"
    BOOKING = "booking"
    FAQ = "faq"
    OBJECTION = "objection"


class GroomingState(TypedDict, total=False):
    user_id: str
    user_message: str

    session: Dict[str, Any]
    intent: str

    extracted_data: Dict[str, Any]
    selected_service: Dict[str, Any]
    available_slots: List[Dict[str, str]]
    booking_day: str
    booking_time: str
    booking_confirmed: bool
    qualified: bool

    reply: str
    errors: List[str]


def empty_session() -> Dict[str, Any]:
    return {
        "lead_id": None,
        "stage": Stages.INITIATED,
        "name": "",
        "phone": "",
        "note": "",
        "city": "",
        "pet": {
            "name": "",
            "breed": "",
            "weight": "",
            "age": "",
            "coat": "",
        },
        "selected_service_id": None,
        "followup_required": False,
    }
