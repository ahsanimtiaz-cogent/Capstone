import json
import logging

from graph.state import GroomingState, Intents, Stages
from prompts.intent_prompt import INTENT_PROMPT
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

VALID_INTENTS = {
    Intents.QUALIFICATION,
    Intents.SERVICE_INQUIRY,
    Intents.BOOKING,
    Intents.FAQ,
    Intents.OBJECTION,
}


def make_detect_intent_node(llm: LLMService):
    def detect_intent_node(state: GroomingState):
        session = state.get("session", {})
        stage = session.get("stage", Stages.INITIATED)

        prompt = INTENT_PROMPT.replace(
            "{user_message}", state["user_message"]
        ).replace(
            "{session_json}", json.dumps(session, indent=2)
        )

        parsed = llm.invoke_json(prompt)
        intent = (parsed or {}).get("intent")

        # Trust the LLM whenever it has a strong opinion (anything other than the
        # default `qualification` fallback). This lets objection/FAQ/booking
        # signals override mid-flow.
        if intent in VALID_INTENTS and intent != Intents.QUALIFICATION:
            return {"intent": intent}

        # LLM said qualification (or returned nothing). Use stage to decide
        # whether to actually treat this as a stage-appropriate signal.
        if stage in (Stages.BOOKING_DAY, Stages.BOOKING_SLOT):
            return {"intent": Intents.BOOKING}
        if stage == Stages.SERVICE_SELECTION:
            return {"intent": Intents.SERVICE_INQUIRY}
        return {"intent": Intents.QUALIFICATION}

    return detect_intent_node
