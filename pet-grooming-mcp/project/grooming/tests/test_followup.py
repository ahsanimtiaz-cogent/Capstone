"""Test 4 — Hesitation → followup is scheduled."""
from project.grooming.models import FollowupJob

from .harness import ConversationRunner


def test_hesitation_schedules_followup(integrations):
    sheets, _calendar = integrations
    convo = ConversationRunner(sheets, user_id="u_followup", display_name="Yusuf")

    convo.send("Hi, dog Milo, Poodle, 7 kg, 4 years old, smooth coat, phone +15552223333")
    assert sheets.leads[0]["status"] == "qualified"

    convo.send("I'll think about it.")
    pending = list(FollowupJob.objects.filter(status=FollowupJob.STATUS_PENDING))
    assert len(pending) >= 1
    assert pending[0].lead_id == sheets.leads[0]["lead_id"]
    assert sheets.leads[0]["status"] in ("qualified", "follow_up", "booked")
