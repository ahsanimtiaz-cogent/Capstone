"""Postgres-backed state for the grooming bot.

`ChatSession` replaces the lang-graph `storage/sessions.json` file:
one row per Discord user, with the per-user funnel state.

`FollowupJob` replaces `storage/followups.json` (the APScheduler
disk-persisted reminder list). Celery is the live executor; this row
is for queryability + idempotency.

`MessageLog` is a thin audit trail of inbound messages and bot replies,
useful for admin debugging — the original project had no equivalent
since it only logged to console.
"""
from django.db import models

from project.core.models import TimestampedModel


def _empty_session_payload() -> dict:
    """Default JSON payload for a brand-new session — mirrors empty_session() in lang-graph."""
    return {
        "lead_id": None,
        "stage": "initiated",
        "name": "",
        "phone": "",
        "city": "",
        "note": "",
        "pet": {"name": "", "breed": "", "weight": "", "age": "", "coat": ""},
        "selected_service_id": None,
        "recommended_service_id": None,
        "booking_day": "",
        "followup_required": False,
    }


class ChatSession(TimestampedModel):
    discord_user_id = models.CharField(max_length=64, unique=True, db_index=True)
    display_name = models.CharField(max_length=255, blank=True, default="")
    payload = models.JSONField(default=_empty_session_payload)

    def __str__(self) -> str:
        return f"ChatSession({self.discord_user_id})"


class FollowupJob(TimestampedModel):
    STATUS_PENDING = "pending"
    STATUS_FIRED = "fired"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_FIRED, "Fired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    job_id = models.CharField(max_length=64, unique=True)
    lead_id = models.CharField(max_length=64, db_index=True)
    discord_user_id = models.CharField(max_length=64, db_index=True)
    message = models.TextField()
    send_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    celery_task_id = models.CharField(max_length=128, blank=True, default="")

    def __str__(self) -> str:
        return f"FollowupJob({self.job_id} lead={self.lead_id})"


class MessageLog(TimestampedModel):
    discord_user_id = models.CharField(max_length=64, db_index=True)
    user_message = models.TextField(blank=True, default="")
    bot_reply = models.TextField(blank=True, default="")
    intent = models.CharField(max_length=32, blank=True, default="")
    stage_before = models.CharField(max_length=32, blank=True, default="")
    stage_after = models.CharField(max_length=32, blank=True, default="")
