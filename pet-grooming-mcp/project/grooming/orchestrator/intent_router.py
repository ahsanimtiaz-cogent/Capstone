"""Intent dispatch — direct port of lang-graph/graph/routers/intent_router.py."""
from .stages import Intents, VALID_INTENTS


def intent_router(intent: str) -> str:
    if intent not in VALID_INTENTS:
        return Intents.QUALIFICATION
    return intent
