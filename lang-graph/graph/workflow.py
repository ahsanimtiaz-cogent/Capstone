from langgraph.graph import StateGraph, END

from graph.state import GroomingState, Intents
from graph.nodes.intent import make_detect_intent_node
from graph.nodes.extract import make_extract_information_node
from graph.nodes.session import make_update_session_node
from graph.nodes.ask_missing import ask_missing_fields_node
from graph.nodes.qualify import make_qualify_lead_node
from graph.nodes.services import make_show_services_node, make_service_selection_node
from graph.nodes.booking import (
    make_show_hours_and_ask_day_node,
    make_fetch_and_show_slots_node,
    make_book_appointment_node,
)
from graph.nodes.faq import make_faq_node
from graph.nodes.objection import make_objection_response_node
from graph.nodes.followup import make_schedule_followup_node

from graph.routers.intent_router import intent_router
from graph.routers.completion_router import completion_router
from graph.routers.booking_router import booking_dispatch, service_inquiry_dispatch

from services.sheets_service import SheetsRepo
from services.calendar_service import CalendarService
from services.llm_service import LLMService
from services.reminder_service import ReminderService


def _passthrough(state: GroomingState):
    """No-op node used as a routing hub for conditional edges.
    LangGraph requires every node to write at least one state channel, so we
    re-emit `intent` unchanged.
    """
    return {"intent": state.get("intent", "")}


def build_graph(sheets: SheetsRepo, calendar: CalendarService,
                llm: LLMService, reminder: ReminderService):
    g = StateGraph(GroomingState)

    # --- Nodes ---
    g.add_node("detect_intent", make_detect_intent_node(llm))
    g.add_node("extract_information", make_extract_information_node(llm))
    g.add_node("update_session", make_update_session_node(sheets))
    g.add_node("ask_missing_fields", ask_missing_fields_node)
    g.add_node("qualify_lead", make_qualify_lead_node(sheets))
    g.add_node("show_services", make_show_services_node(sheets))
    g.add_node("select_service", make_service_selection_node(sheets))
    g.add_node("show_hours_ask_day", make_show_hours_and_ask_day_node(sheets))
    g.add_node("fetch_slots", make_fetch_and_show_slots_node(sheets, calendar))
    g.add_node("book_appointment", make_book_appointment_node(sheets, calendar))
    g.add_node("faq", make_faq_node(sheets, llm))
    g.add_node("objection", make_objection_response_node(sheets, llm))
    g.add_node("schedule_followup", make_schedule_followup_node(sheets, reminder))

    # Routing hubs (pass-through; their job is to fan out via conditional edges)
    g.add_node("booking_dispatch", _passthrough)
    g.add_node("service_inquiry_dispatch", _passthrough)

    # --- Topology ---
    g.set_entry_point("detect_intent")

    g.add_conditional_edges(
        "detect_intent",
        intent_router,
        {
            Intents.QUALIFICATION: "extract_information",
            Intents.SERVICE_INQUIRY: "service_inquiry_dispatch",
            Intents.BOOKING: "booking_dispatch",
            Intents.FAQ: "faq",
            Intents.OBJECTION: "objection",
        },
    )

    # Qualification flow
    g.add_edge("extract_information", "update_session")
    g.add_conditional_edges(
        "update_session",
        completion_router,
        {
            "qualified": "qualify_lead",
            "incomplete": "ask_missing_fields",
        },
    )
    g.add_edge("ask_missing_fields", END)
    g.add_edge("qualify_lead", END)

    # Service inquiry: stage-aware
    g.add_conditional_edges(
        "service_inquiry_dispatch",
        service_inquiry_dispatch,
        {
            "show_services": "show_services",
            "select_service": "select_service",
        },
    )
    g.add_edge("show_services", END)
    g.add_edge("select_service", END)

    # Booking: stage-aware. Notably can route to "extract" if user isn't qualified yet.
    g.add_conditional_edges(
        "booking_dispatch",
        booking_dispatch,
        {
            "extract": "extract_information",
            "show_services": "show_services",
            "select_service": "select_service",
            "show_hours": "show_hours_ask_day",
            "fetch_slots": "fetch_slots",
            "book": "book_appointment",
            "end": END,
        },
    )
    g.add_edge("show_hours_ask_day", END)
    g.add_edge("fetch_slots", END)
    g.add_edge("book_appointment", END)

    # FAQ
    g.add_edge("faq", END)

    # Objection → schedule follow-up DM
    g.add_edge("objection", "schedule_followup")
    g.add_edge("schedule_followup", END)

    return g.compile()
