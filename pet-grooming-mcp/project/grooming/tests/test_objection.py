"""Test 3 — Objection routing + follow-up scheduling."""
from project.grooming.models import FollowupJob

from .harness import ConversationRunner


def test_objection_routes_to_objection_node(integrations):
    sheets, _calendar = integrations
    convo = ConversationRunner(sheets, user_id="u_obj", display_name="Iris")

    convo.send("Hi, dog Bella, Poodle, 8 kg, 3 years old, matted coat, phone +15551112222")
    reply = convo.send("That's too expensive.")
    assert any(token in reply.lower() for token in ("lighter", "transparent", "pricing", "bath")), \
        f"unexpected objection reply: {reply}"

    pending = list(FollowupJob.objects.filter(status=FollowupJob.STATUS_PENDING))
    assert len(pending) == 1
    assert pending[0].lead_id == sheets.leads[0]["lead_id"]
