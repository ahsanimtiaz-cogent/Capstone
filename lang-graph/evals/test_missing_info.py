"""Test Case 2 — Missing Info.

Customer: "I need grooming." — bot must keep asking until breed/weight/age/coat
+ phone are provided, then continue the booking flow.
"""
from evals.harness import make_runtime, ConversationRunner


def test_missing_info_keeps_asking_until_qualified():
    graph, sheets, _calendar, _llm, _reminder = make_runtime()
    convo = ConversationRunner(graph, sheets, user_id="u_missing", display_name="Sam")

    convo.send("I need grooming.")
    assert sheets.leads[0]["status"] == "initiated"

    # Provide only some fields — bot should still ask for the rest
    convo.send("It's a Husky.")
    assert convo.session["stage"] in ("initiated", "qualifying")
    assert sheets.leads[0]["status"] in ("initiated",), \
        "should not qualify with breed alone"

    # Provide more — still missing fields
    convo.send("She's 18 kg and 2 years old.")
    assert sheets.leads[0]["status"] in ("initiated",), \
        "should not qualify without coat + phone"

    # Final fields → qualify
    convo.send("Coat is normal, phone +15559876543, her name is Luna.")
    assert sheets.leads[0]["status"] == "qualified"
    # Pet row should be saved exactly once with the breed
    pets = sheets.list_pets_for_lead(sheets.leads[0]["lead_id"])
    assert len(pets) == 1
    assert pets[0]["breed"].lower() == "husky"
