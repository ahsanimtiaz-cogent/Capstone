"""Celery tasks — replaces the in-process APScheduler in lang-graph.

`send_followup` is scheduled with `apply_async(eta=...)` by the
`followup.schedule_followup` MCP tool. When it fires, it loads the
FollowupJob row, marks it as fired/cancelled, and DMs the user via the
DiscordSender helper.
"""
import asyncio
import logging

from celery import shared_task
from django.conf import settings

from .models import FollowupJob

logger = logging.getLogger(__name__)


@shared_task(name="grooming.send_followup")
def send_followup(job_id: str) -> dict:
    try:
        job = FollowupJob.objects.get(job_id=job_id)
    except FollowupJob.DoesNotExist:
        return {"fired": False, "error": "job_not_found"}

    if job.status != FollowupJob.STATUS_PENDING:
        return {"fired": False, "error": f"status={job.status}"}

    token = getattr(settings, "DISCORD_TOKEN", "")
    if not token:
        logger.warning("DISCORD_TOKEN not set — cannot deliver followup %s", job_id)
        return {"fired": False, "error": "missing_token"}

    from .bot.sender import DiscordSender
    sender = DiscordSender(token=token)
    try:
        asyncio.run(sender.send(job.discord_user_id, job.message))
        job.status = FollowupJob.STATUS_FIRED
        job.save(update_fields=["status"])
        return {"fired": True, "job_id": job_id}
    except Exception as e:
        logger.exception("Followup delivery failed for %s: %s", job_id, e)
        return {"fired": False, "error": str(e)}
