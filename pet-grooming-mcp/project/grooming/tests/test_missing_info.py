"""Test 2 — Missing info. Ported from lang-graph/evals/test_missing_info.py."""
from .harness import ConversationRunner


def test_missing_info_keeps_asking_until_qualified(integrations):
    sheets, _calendar = integrations
    convo = ConversationRunner(sheets, user_id="u_missing", display_name="Sam")

    convo.send("I need grooming.")
    assert sheets.leads[0]["status"] == "initiated"

    convo.send("It's a Husky.")
    assert convo.session["stage"] in ("initiated", "qualifying")
    assert sheets.leads[0]["status"] == "initiated", \
        "should not qualify with breed alone"

    convo.send("She's 18 kg and 2 years old.")
    assert sheets.leads[0]["status"] == "initiated", \
        "should not qualify without coat + phone"

    convo.send("Coat is normal, phone +15559876543, her name is Luna.")
    assert sheets.leads[0]["status"] == "qualified"
    pets = sheets.list_pets_for_lead(sheets.leads[0]["lead_id"])
    assert len(pets) == 1
    assert pets[0]["breed"].lower() == "husky"
