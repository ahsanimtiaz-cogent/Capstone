import logging

from graph.state import GroomingState, Stages
from services.matching_service import find_best_service, format_services_list
from services.sheets_service import SheetsRepo

logger = logging.getLogger(__name__)


def make_qualify_lead_node(sheets: SheetsRepo):
    def qualify_lead_node(state: GroomingState):
        session = dict(state.get("session", {}))
        lead_id = session.get("lead_id")

        if lead_id:
            try:
                sheets.set_lead_status(lead_id, "qualified")
            except Exception as e:
                logger.warning("Could not flip lead status: %s", e)

            try:
                existing = sheets.list_pets_for_lead(lead_id)
                pet = session.get("pet", {})
                pet_signature = (
                    pet.get("name", "").strip().lower(),
                    pet.get("breed", "").strip().lower(),
                )
                already = any(
                    (p.get("pet_name", "").strip().lower(),
                     p.get("breed", "").strip().lower()) == pet_signature
                    for p in existing
                )
                if not already:
                    sheets.append_pet(lead_id, {
                        "name": pet.get("name", ""),
                        "breed": pet.get("breed", ""),
                        "weight": pet.get("weight", ""),
                        "age": pet.get("age", ""),
                        "coat": pet.get("coat", ""),
                        "notes": session.get("note", ""),
                    })
            except Exception as e:
                logger.warning("Could not append pet record: %s", e)

        session["stage"] = Stages.QUALIFIED

        services = sheets.list_services()
        if not services:
            return {
                "qualified": True,
                "session": session,
                "reply": "You're all set! We're updating our service menu — I'll be back shortly.",
            }

        pet = session.get("pet", {})
        recommended = find_best_service(pet, services)
        services_text = format_services_list(
            services, pet,
            recommended_id=recommended["service_id"] if recommended else None,
        )

        rec_line = ""
        if recommended:
            rec_line = (
                f"\n\nRecommended for {pet.get('name') or 'your pet'}: "
                f"**{recommended['title']}** — ${recommended['final_price']:.2f} "
                f"({recommended['duration_min']} min)."
            )
            if recommended.get("is_fallback") and recommended.get("fallback_reason"):
                rec_line += f"\n_{recommended['fallback_reason']}_"

        reply = (
            "Great — you're qualified! Here's what we offer:\n\n"
            f"{services_text}"
            f"{rec_line}\n\n"
            "Which one would you like, or want to know more about a specific service?"
        )

        session["stage"] = Stages.SERVICE_SELECTION
        if recommended:
            session["recommended_service_id"] = recommended["service_id"]

        return {
            "qualified": True,
            "session": session,
            "reply": reply,
            "selected_service": {},
        }

    return qualify_lead_node
