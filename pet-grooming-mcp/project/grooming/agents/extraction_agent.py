"""ExtractionAgent — pull customer + pet fields from free text.

Replaces lang-graph/graph/nodes/extract.py. Returns the same shape as the
original Gemini JSON contract: ({"data": {...}, "message": "..."}).
"""
import json
import re
from typing import Any, Dict, Tuple

from pydantic import BaseModel, Field

from ._llm import build_agent, unwrap
from .prompts.extraction import EXTRACTION_SYSTEM_PROMPT


class PetData(BaseModel):
    name: str = ""
    breed: str = ""
    weight: str = ""
    age: str = ""
    coat: str = ""


class ExtractedData(BaseModel):
    name: str = ""
    phone: str = ""
    note: str = ""
    pet: PetData = Field(default_factory=PetData)


class ExtractionResult(BaseModel):
    data: ExtractedData
    message: str = ""


class ExtractionAgent:
    def __init__(self) -> None:
        self._agent = build_agent(ExtractionResult, EXTRACTION_SYSTEM_PROMPT)

    def extract(self, user_message: str, session: Dict[str, Any]
                ) -> Tuple[Dict[str, Any], str]:
        if self._agent is not None:
            try:
                user_prompt = (
                    f"CURRENT SESSION:\n{json.dumps(session, indent=2, default=str)}\n\n"
                    f"USER MESSAGE:\n{user_message}"
                )
                result = self._agent.run_sync(user_prompt)
                payload = unwrap(result)
                return payload.data.model_dump(), payload.message
            except Exception:
                pass
        return self._fallback(user_message, session)

    # ---- Deterministic fallback (matches ScriptedLLM in lang-graph/evals/fakes.py) -------

    @staticmethod
    def _fallback(user_message: str, session: Dict[str, Any]
                  ) -> Tuple[Dict[str, Any], str]:
        msg = user_message or ""
        lower = msg.lower()
        data: Dict[str, Any] = {
            "name": "", "phone": "", "note": "",
            "pet": {"name": "", "breed": "", "weight": "", "age": "", "coat": ""},
        }

        phone = re.search(r"(\+?\d[\d\- ]{6,}\d)", msg)
        if phone:
            data["phone"] = re.sub(r"[\s\-]", "", phone.group(1))

        breed_match = re.search(
            r"\b(husky|poodle|shih tzu|german shepherd|labrador|bulldog|mixed|maltese)\b",
            lower,
        )
        if breed_match:
            data["pet"]["breed"] = breed_match.group(1).title()

        weight_match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|lbs?)", lower)
        if weight_match:
            data["pet"]["weight"] = f"{weight_match.group(1)} {weight_match.group(2)}"

        age_match = re.search(r"(\d+(?:\.\d+)?)\s*(year|years|yr|yrs|month|months|mo)", lower)
        if age_match:
            data["pet"]["age"] = f"{age_match.group(1)} {age_match.group(2)}"

        coat_match = re.search(
            r"\b(matted|smooth|curly|heavy[_ -]?shed|mild[_ -]?shed|normal|rough)\b", lower
        )
        if coat_match:
            data["pet"]["coat"] = coat_match.group(1).replace(" ", "_").replace("-", "_")

        breed_text = breed_match.group(1).lower() if breed_match else ""
        stopwords = {breed_text, "grooming", "the", "her", "his", "i", "a"}
        name_patterns = [
            r"\b(?:dog|pet|pup|cat)\s+(?:named|called)\s+([A-Z][a-z]+)",
            r"\bmy\s+(?:dog|pet|pup)\s+([A-Z][a-zA-Z]+)\b",
            r"\bfor\s+(?:my\s+(?:dog|pet|pup)\s+)?([A-Z][a-zA-Z]+)\b",
            r"\b(?:dog|pet|pup|cat)\s+([A-Z][a-zA-Z]+)\b",
            r"\b(?:her|his|its)?\s*name\s+is\s+([A-Z][a-zA-Z]+)",
        ]
        for pat in name_patterns:
            m_name = re.search(pat, msg)
            if m_name:
                candidate = m_name.group(1)
                if candidate.lower() not in stopwords:
                    data["pet"]["name"] = candidate
                    break

        # Carry forward existing session values when the new turn didn't override.
        for k in ("name", "phone"):
            if session.get(k) and not data.get(k):
                data[k] = session[k]
        pet_existing = session.get("pet", {}) or {}
        for k in ("name", "breed", "weight", "age", "coat"):
            if pet_existing.get(k) and not data["pet"].get(k):
                data["pet"][k] = pet_existing[k]

        missing = []
        if not data.get("phone"):
            missing.append("phone")
        for f in ("breed", "weight", "age", "coat"):
            if not data["pet"].get(f):
                missing.append(f)
        message = "Got it!" if not missing else "Could you share: " + ", ".join(missing) + "?"
        return data, message
