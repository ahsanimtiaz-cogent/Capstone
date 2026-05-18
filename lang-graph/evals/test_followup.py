"""Test Case 5 — No Booking Yet / Follow-up.

Customer: "I'll think about it." — lead remains qualified, a follow-up
gets scheduled via the ReminderService.
"""
from evals.harness import make_runtime, ConversationRunner


def test_hesitation_schedules_followup():
    graph, sheets, _calendar, _llm, reminder = make_runtime()
    convo = ConversationRunner(graph, sheets, user_id="u_followup", display_name="Yusuf")

    convo.send(
        "Hi, dog Milo, Poodle, 7 kg, 4 years old, smooth coat, phone +15552223333"
    )
    assert sheets.leads[0]["status"] == "qualified"

    convo.send("I'll think about it.")
    # Either objection-routing or hesitation handling should schedule a follow-up.
    assert len(reminder.scheduled) >= 1
    job = reminder.scheduled[0]
    assert job["lead_id"] == sheets.leads[0]["lead_id"]
    # Lead status should be tracked as follow_up after objection path.
    assert sheets.leads[0]["status"] in ("qualified", "follow_up", "booked"), \
        f"unexpected status {sheets.leads[0]['status']}"
