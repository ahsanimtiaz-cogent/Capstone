from graph.state import GroomingState
from prompts.faq_prompt import FAQ_PROMPT
from services.llm_service import LLMService
from services.sheets_service import SheetsRepo


def make_faq_node(sheets: SheetsRepo, llm: LLMService):
    def faq_node(state: GroomingState):
        brand = sheets.get_brand_config()
        prompt = (
            FAQ_PROMPT
            .replace("{brand_name}", brand.get("brand_name", "Paws & Relax"))
            .replace("{hours}", brand.get("hours", ""))
            .replace("{location}", brand.get("location", ""))
            .replace("{timezone}", brand.get("timezone", ""))
            .replace("{user_message}", state.get("user_message", ""))
        )
        try:
            answer = llm.invoke(prompt).strip()
        except Exception:
            answer = (
                f"We're at {brand.get('location','')} during {brand.get('hours','')}. "
                "Let me know how else I can help!"
            )
        return {"reply": answer or "Happy to help — what would you like to know?"}
    return faq_node
