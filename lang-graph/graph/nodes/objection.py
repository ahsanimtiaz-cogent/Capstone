import json
import logging

from graph.state import GroomingState
from prompts.objection_prompt import OBJECTION_CLASSIFY_PROMPT, OBJECTION_RESPONSE_PROMPT
from services.llm_service import LLMService
from services.sheets_service import SheetsRepo

logger = logging.getLogger(__name__)

VALID_OBJECTIONS = {"price", "hesitation", "value_doubt", "other"}


def make_objection_response_node(sheets: SheetsRepo, llm: LLMService):
    def objection_node(state: GroomingState):
        brand = sheets.get_brand_config()
        snippets = brand.get("objection_snippets_json", {}) or {}
        user_message = state.get("user_message", "")

        # Classify
        classify_prompt = OBJECTION_CLASSIFY_PROMPT.replace("{user_message}", user_message)
        parsed = llm.invoke_json(classify_prompt) or {}
        category = parsed.get("objection") if parsed.get("objection") in VALID_OBJECTIONS else "other"

        snippet_key = "price" if category == "price" else (
            "time" if category == "hesitation" else "anxious"
        )
        snippet = snippets.get(snippet_key) or snippets.get("price") or ""

        selected = state.get("selected_service") or {}
        service_summary = (
            f"{selected.get('title','(none chosen)')} — ${selected.get('final_price', selected.get('base_price', 0)):.2f}"
            if selected else "(no service selected yet)"
        )

        response_prompt = (
            OBJECTION_RESPONSE_PROMPT
            .replace("{brand_name}", brand.get("brand_name", "Paws & Relax"))
            .replace("{objection_category}", category)
            .replace("{snippet}", snippet)
            .replace("{user_message}", user_message)
            .replace("{service_summary}", service_summary)
        )

        try:
            text = llm.invoke(response_prompt).strip()
        except Exception:
            text = (
                "Totally hear you. We keep pricing matched to coat and weight, "
                "and we can also suggest a lighter package if you'd like."
            )

        session = dict(state.get("session", {}))
        session["followup_required"] = True

        return {
            "session": session,
            "reply": text or "Got it — happy to walk through any concerns.",
        }
    return objection_node
