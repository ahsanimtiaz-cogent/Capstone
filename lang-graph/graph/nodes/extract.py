import json
import logging

from graph.state import GroomingState
from prompts.extraction_prompt import EXTRACTION_PROMPT
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


def make_extract_information_node(llm: LLMService):
    def extract_information_node(state: GroomingState):
        prompt = EXTRACTION_PROMPT.replace(
            "{session_json}", json.dumps(state.get("session", {}), indent=2)
        ).replace(
            "{user_message}", state["user_message"]
        )

        parsed = llm.invoke_json(prompt)
        if not parsed:
            return {
                "extracted_data": {},
                "reply": "I had trouble understanding that — could you rephrase?",
            }

        return {
            "extracted_data": parsed.get("data", {}) or {},
            "reply": parsed.get("message", "") or "",
        }

    return extract_information_node
