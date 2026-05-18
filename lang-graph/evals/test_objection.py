"""Test Case 4 — Objection.

Customer: "That's too expensive." — bot routes to the objection branch,
classifies as 'price', and replies using the BrandConfig snippet pattern.
A follow-up should also get scheduled.
"""
from evals.harness import make_runtime, ConversationRunner


def test_objection_routes_to_objection_node():
    graph, sheets, _calendar, llm, reminder = make_runtime()
    convo = ConversationRunner(graph, sheets, user_id="u_obj", display_name="Iris")

    # First qualify quickly so the user has a real session
    convo.send(
        "Hi, dog Bella, Poodle, 8 kg, 3 years old, matted coat, phone +15551112222"
    )
    # The qualify_lead reply lists services — now object
    reply = convo.send("That's too expensive.")
    assert convo.last_state.get("intent") == "objection"
    # The response should be the canned text from our ScriptedLLM
    assert "lighter" in reply.lower() or "transparent" in reply.lower() \
        or "pricing" in reply.lower()

    # Follow-up should have been scheduled
    assert len(reminder.scheduled) == 1
    assert reminder.scheduled[0]["lead_id"] == sheets.leads[0]["lead_id"]
