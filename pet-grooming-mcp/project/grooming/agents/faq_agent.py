"""FaqAgent — concise (1-3 sentence) answer grounded in BrandConfig.

Replaces lang-graph/graph/nodes/faq.py. The MCP `knowledge.get_brand_config`
tool supplies the facts; this agent paraphrases.
"""
from pydantic import BaseModel

from ._llm import build_agent, unwrap
from .prompts.faq import FAQ_SYSTEM_PROMPT


class FaqResult(BaseModel):
    answer: str


class FaqAgent:
    def __init__(self) -> None:
        self._agent = build_agent(FaqResult, FAQ_SYSTEM_PROMPT)

    def answer(self, *, user_message: str, brand_name: str, hours: str,
               location: str, timezone: str) -> str:
        if self._agent is not None:
            try:
                user_prompt = (
                    f"BUSINESS FACTS:\n"
                    f"- Brand: {brand_name}\n"
                    f"- Hours: {hours}\n"
                    f"- Location: {location}\n"
                    f"- Timezone: {timezone}\n\n"
                    f"USER QUESTION:\n{user_message}"
                )
                result = self._agent.run_sync(user_prompt)
                text = unwrap(result).answer.strip()
                if text:
                    return text
            except Exception:
                pass
        return self._fallback(brand_name, hours, location, timezone)

    @staticmethod
    def _fallback(brand_name: str, hours: str, location: str, timezone: str) -> str:
        return (
            f"We're open {hours} at {location}. Time zone: {timezone}."
            if hours or location else
            f"Happy to help — what would you like to know about {brand_name}?"
        )
