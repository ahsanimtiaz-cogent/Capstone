"""Test Case 1 — Standard Booking.

Customer: "Hi, I need grooming for my dog Bella."
Expected: New lead record → collect details → show services → show times
          → confirm booking → status flips to booked, both Sheet + Calendar updated.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from evals.harness import make_runtime, ConversationRunner


def _next_weekday(weekday: int = 2) -> str:
    """Pick the next date that is Wed (weekday=2) so we're inside Mon-Sat hours."""
    today = datetime.now(ZoneInfo("Asia/Karachi")).date()
    delta = (weekday - today.weekday()) % 7 or 7
    return (today + timedelta(days=delta)).strftime("%Y-%m-%d")


def test_standard_booking_end_to_end():
    graph, sheets, calendar, llm, reminder = make_runtime()
    convo = ConversationRunner(graph, sheets, user_id="u_standard", display_name="Asha")

    # Turn 1: greeting + initial pet mention
    convo.send("Hi, I need grooming for my dog Bella")
    # Turn 2: provide pet attributes + phone in one message
    convo.send(
        "Bella is a Poodle, 8 kg, 3 years old, with a matted coat. "
        "My phone is +15551234567"
    )

    # After qualification, status should be qualified and services should be shown
    lead = sheets.leads[0]
    assert lead["status"] == "qualified", f"expected qualified, got {lead['status']}"
    assert any("Full Groom" in h["bot"] for h in convo.history), \
        "services list should be shown after qualification"

    # Turn 3: pick a service
    convo.send("Full Groom please")
    assert convo.session["stage"] == "booking_day"

    # Turn 4: pick a day
    day = _next_weekday()
    convo.send(f"Let's do {day}")
    slots = convo.last_state.get("available_slots") or []
    assert slots, "should have available slots for an empty calendar day"

    # Turn 5: pick the first slot's start time
    first_start = slots[0]["start_label"]
    reply = convo.send(first_start)

    # Booking should succeed: appointment row + calendar event + status=booked
    assert convo.last_state.get("booking_confirmed") is True, \
        f"booking not confirmed; reply was: {reply}"
    assert len(sheets.appointments) == 1
    appt = sheets.appointments[0]
    assert appt["status"] == "booked"
    assert appt["calendar_event_id"]
    assert appt["scheduled_at_iso"].startswith(day)
    assert sheets.leads[0]["status"] == "booked"
    assert len(calendar.events) == 1
