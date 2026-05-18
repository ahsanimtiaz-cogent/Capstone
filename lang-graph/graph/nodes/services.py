import logging

from graph.state import GroomingState, Stages
from services.matching_service import (
    find_best_service,
    format_services_list,
    match_service_by_user_input,
    price_for_service,
)
from services.sheets_service import SheetsRepo

logger = logging.getLogger(__name__)


def make_show_services_node(sheets: SheetsRepo):
    def show_services_node(state: GroomingState):
        services = sheets.list_services()
        if not services:
            return {
                "reply": "Our service menu is being updated — please check back shortly.",
            }
        session = state.get("session", {})
        pet = session.get("pet", {})
        recommended = find_best_service(pet, services) if pet.get("breed") else None
        services_text = format_services_list(
            services, pet,
            recommended_id=recommended["service_id"] if recommended else None,
        )
        rec_line = ""
        if recommended:
            rec_line = (
                f"\n\nRecommended: **{recommended['title']}** — "
                f"${recommended['final_price']:.2f} ({recommended['duration_min']} min)."
            )
            if recommended.get("is_fallback") and recommended.get("fallback_reason"):
                rec_line += f"\n_{recommended['fallback_reason']}_"

        return {
            "reply": "Here are our services:\n\n" + services_text + rec_line,
        }
    return show_services_node


def make_service_selection_node(sheets: SheetsRepo):
    """Parse the user's free-text selection into a chosen service."""
    def service_selection_node(state: GroomingState):
        session = dict(state.get("session", {}))
        services = sheets.list_services()
        if not services:
            return {
                "reply": "Our service menu is unavailable — please try again in a moment.",
            }

        user_text = state.get("user_message", "")
        pet = session.get("pet", {})

        chosen = match_service_by_user_input(user_text, services)
        if chosen is None:
            # Treat "yes" / "ok" / "sure" as accepting the recommendation
            affirmatives = {"yes", "y", "yeah", "sure", "ok", "okay", "please", "go ahead"}
            if user_text.strip().lower() in affirmatives:
                rec_id = session.get("recommended_service_id")
                if rec_id:
                    chosen = sheets.get_service(rec_id)

        if chosen is None:
            services_text = format_services_list(services, pet)
            return {
                "reply": (
                    "I didn't catch which service you'd like. Here are the options again:\n\n"
                    + services_text
                    + "\n\nWhich would you like?"
                ),
            }

        final_price, is_fallback, fallback_reason = price_for_service(chosen, pet)
        selected = {
            "service_id": chosen["service_id"],
            "title": chosen["title"],
            "base_price": chosen["base_price"],
            "final_price": final_price,
            "duration_min": chosen["duration_min"],
            "is_fallback": is_fallback,
            "fallback_reason": fallback_reason,
        }
        session["selected_service_id"] = chosen["service_id"]
        session["stage"] = Stages.BOOKING_DAY

        fb_note = ""
        if is_fallback and fallback_reason:
            fb_note = f"\n_{fallback_reason}_"

        return {
            "session": session,
            "selected_service": selected,
            "reply": (
                f"Great choice — **{chosen['title']}** "
                f"(${final_price:.2f}, {chosen['duration_min']} min).{fb_note}\n\n"
                "Which day works for you? Please send a date in YYYY-MM-DD format."
            ),
        }
    return service_selection_node
