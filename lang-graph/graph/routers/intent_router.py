from graph.state import GroomingState, Intents


def intent_router(state: GroomingState) -> str:
    intent = state.get("intent") or Intents.QUALIFICATION
    if intent not in {
        Intents.QUALIFICATION,
        Intents.SERVICE_INQUIRY,
        Intents.BOOKING,
        Intents.FAQ,
        Intents.OBJECTION,
    }:
        return Intents.QUALIFICATION
    return intent
