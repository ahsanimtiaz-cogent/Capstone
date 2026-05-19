"""ObjectionAgent — empathetic 2-4 sentence reply using BrandConfig snippets.

Replaces lang-graph/graph/nodes/objection.py.
"""
from typing import Dict

from pydantic import BaseModel

from ._llm import build_agent, unwrap
from .prompts.objection import OBJECTION_CLASSIFY_PROMPT, OBJECTION_RESPONSE_PROMPT


VALID_CATEGORIES = {"price", "hesitation", "value_doubt", "other"}


class ObjectionClassification(BaseModel):
    objection: str  # price | hesitation | value_doubt | other


class ObjectionResponse(BaseModel):
    reply: str


class ObjectionAgent:
    def __init__(self) -> None:
        self._classifier = build_agent(ObjectionClassification, OBJECTION_CLASSIFY_PROMPT)
        self._responder = build_agent(ObjectionResponse, OBJECTION_RESPONSE_PROMPT)

    def respond(self, *, user_message: str, brand_name: str,
                objection_snippets: Dict[str, str], service_summary: str) -> str:
        category = self._classify(user_message)
        snippet_key = "price" if category == "price" else (
            "time" if category == "hesitation" else "anxious"
        )
        snippet = objection_snippets.get(snippet_key) or objection_snippets.get("price") or ""

        if self._responder is not None:
            try:
                user_prompt = (
                    f"Brand: {brand_name}\n"
                    f"Objection category: {category}\n"
                    f"Relevant snippet (inspiration, do not quote verbatim):\n"
                    f"\"{snippet}\"\n\n"
                    f"User's last message:\n\"{user_message}\"\n\n"
                    f"Service summary: {service_summary}"
                )
                result = self._responder.run_sync(user_prompt)
                text = unwrap(result).reply.strip()
                if text:
                    return text
            except Exception:
                pass

        return (
            "Totally hear you — we keep pricing matched to coat and weight. "
            "Would a lighter Bath & Brush work instead?"
        )

    def _classify(self, user_message: str) -> str:
        if self._classifier is not None:
            try:
                result = self._classifier.run_sync(f"USER MESSAGE:\n{user_message}")
                value = unwrap(result).objection.strip().lower()
                if value in VALID_CATEGORIES:
                    return value
            except Exception:
                pass
        m = (user_message or "").lower()
        if "expensive" in m or "pricey" in m or "discount" in m:
            return "price"
        if "think" in m or "later" in m:
            return "hesitation"
        return "other"
