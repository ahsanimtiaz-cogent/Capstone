from graph.state import GroomingState, Stages


def booking_dispatch(state: GroomingState) -> str:
    """Pick the right entry node for a BOOKING-intent message based on stage."""
    session = state.get("session", {})
    stage = session.get("stage", Stages.INITIATED)

    if stage == Stages.BOOKED:
        return "end"

    if stage in (Stages.INITIATED, Stages.QUALIFYING):
        return "extract"        # qualify first

    if stage == Stages.QUALIFIED:
        return "show_services"  # need to pick a service first

    if stage == Stages.SERVICE_SELECTION:
        return "select_service"

    if stage == Stages.BOOKING_DAY:
        return "fetch_slots"

    if stage == Stages.BOOKING_SLOT:
        return "book"

    return "show_hours"


def service_inquiry_dispatch(state: GroomingState) -> str:
    """For SERVICE_INQUIRY intent: pick selection vs. browse."""
    session = state.get("session", {})
    stage = session.get("stage", Stages.INITIATED)

    if stage == Stages.SERVICE_SELECTION:
        return "select_service"
    return "show_services"
