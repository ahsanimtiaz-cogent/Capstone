"""IntentAgent — classify a user message into one of five intents.

Replaces lang-graph/graph/nodes/intent.py + lang-graph/prompts/intent_prompt.py.
Falls back to a regex-based rule set when the LLM key isn't configured.
"""
import json
from typing import Any, Dict

from pydantic import BaseModel, Field

from ..orchestrator.stages import VALID_INTENTS, Intents
from ._llm import build_agent, unwrap
from .prompts.intent import INTENT_SYSTEM_PROMPT


class IntentResult(BaseModel):
    intent: str = Field(description="One of: qualification, service_inquiry, booking, faq, objection")


class IntentAgent:
    def __init__(self) -> None:
        self._agent = build_agent(IntentResult, INTENT_SYSTEM_PROMPT)

    def classify(self, user_message: str, session: Dict[str, Any]) -> str:
        if self._agent is not None:
            try:
                user_prompt = (
                    f"USER MESSAGE:\n{user_message}\n\n"
                    f"CURRENT SESSION:\n{json.dumps(session, indent=2, default=str)}"
                )
                result = self._agent.run_sync(user_prompt)
                value = unwrap(result).intent.strip().lower()
                if value in VALID_INTENTS:
                    return value
            except Exception:
                pass
        return self._fallback(user_message)

    @staticmethod
    def _fallback(user_message: str) -> str:
        m = (user_message or "").lower()
        if any(w in m for w in ["too expensive", "expensive", "pricey", "think about", "discount"]):
            return Intents.OBJECTION
        if any(w in m for w in ["hours", "location", "where are you", "open", "address"]):
            return Intents.FAQ
        if any(w in m for w in ["book", "saturday", "tomorrow", "appointment",
                                "available", "slot", "schedule"]):
            return Intents.BOOKING
        if any(w in m for w in ["service", "price", "cost", "package", "options"]):
            return Intents.SERVICE_INQUIRY
        return Intents.QUALIFICATION
