"""Test 1 — Standard booking end-to-end. Ported from lang-graph/evals/test_standard_booking.py."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .harness import ConversationRunner


def _next_weekday(weekday: int = 2) -> str:
    today = datetime.now(ZoneInfo("Asia/Karachi")).date()
    delta = (weekday - today.weekday()) % 7 or 7
    return (today + timedelta(days=delta)).strftime("%Y-%m-%d")


def test_standard_booking_end_to_end(integrations):
    sheets, calendar = integrations
    convo = ConversationRunner(sheets, user_id="u_standard", display_name="Asha")

    convo.send("Hi, I need grooming for my dog Bella")
    convo.send(
        "Bella is a Poodle, 8 kg, 3 years old, with a matted coat. "
        "My phone is +15551234567"
    )

    lead = sheets.leads[0]
    assert lead["status"] == "qualified", f"expected qualified, got {lead['status']}"
    assert any("Full Groom" in h["bot"] for h in convo.history), \
        "services list should be shown after qualification"

    convo.send("Full Groom please")
    assert convo.session["stage"] == "booking_day"

    day = _next_weekday()
    convo.send(f"Let's do {day}")

    # The coordinator stores the chosen service id in the session; fetch a slot
    # from the calendar fake for that day, then ask the bot to book it.
    svc_id = convo.session.get("selected_service_id")
    svc = sheets.get_service(svc_id)
    slots = calendar.get_free_slots(day, svc["duration_min"], sheets.get_brand_config()["hours"], "Asia/Karachi")
    assert slots, "should have available slots for an empty calendar day"

    first_start = slots[0]["start_label"]
    reply = convo.send(first_start)

    assert convo.session.get("stage") == "booked", \
        f"booking not confirmed; reply was: {reply}"
    assert len(sheets.appointments) == 1
    appt = sheets.appointments[0]
    assert appt["status"] == "booked"
    assert appt["calendar_event_id"]
    assert appt["scheduled_at_iso"].startswith(day)
    assert sheets.leads[0]["status"] == "booked"
    assert len(calendar.events) == 1
