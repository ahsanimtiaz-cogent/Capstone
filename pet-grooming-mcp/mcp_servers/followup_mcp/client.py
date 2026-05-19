"""Followup business logic.

Replaces lang-graph's APScheduler-backed ReminderService with a Postgres
row + a Celery task. Idempotency (no duplicate followups per lead) is
preserved.
"""
import uuid
from datetime import timedelta

from django.utils import timezone

from project.grooming.models import FollowupJob

from ..base_client import BaseMCPClient
from .models import (
    CancelFollowupRequest,
    CancelFollowupResponse,
    FollowupJobOut,
    ListFollowupsRequest,
    ListFollowupsResponse,
    ScheduleFollowupRequest,
    ScheduleFollowupResponse,
)


class FollowupMCPClient(BaseMCPClient):

    def schedule_followup(
        self, request: ScheduleFollowupRequest
    ) -> ScheduleFollowupResponse:
        if not self.lead_id or not self.discord_user_id:
            return ScheduleFollowupResponse(
                scheduled=False, error="Missing _lead_id or _discord_user_id."
            )

        # Idempotency: one pending follow-up per lead.
        existing = FollowupJob.objects.filter(
            lead_id=self.lead_id, status=FollowupJob.STATUS_PENDING
        ).first()
        if existing:
            return ScheduleFollowupResponse(
                scheduled=True, job_id=existing.job_id, duplicate=True,
            )

        send_at = timezone.now() + timedelta(hours=request.delay_hours)
        job_id = f"fu_{uuid.uuid4().hex[:10]}"
        job = FollowupJob.objects.create(
            job_id=job_id,
            lead_id=self.lead_id,
            discord_user_id=self.discord_user_id,
            message=request.message,
            send_at=send_at,
        )

        # Schedule the Celery task (eta-based delivery).
        from project.grooming.tasks import send_followup
        async_result = send_followup.apply_async((job.job_id,), eta=send_at)
        job.celery_task_id = async_result.id
        job.save(update_fields=["celery_task_id"])

        return ScheduleFollowupResponse(scheduled=True, job_id=job_id)

    def list_followups(
        self, _request: ListFollowupsRequest
    ) -> ListFollowupsResponse:
        qs = FollowupJob.objects.filter(status=FollowupJob.STATUS_PENDING)
        if self.lead_id:
            qs = qs.filter(lead_id=self.lead_id)
        return ListFollowupsResponse(jobs=[
            FollowupJobOut(
                job_id=j.job_id,
                lead_id=j.lead_id,
                discord_user_id=j.discord_user_id,
                message=j.message,
                send_at_iso=j.send_at.isoformat(),
                status=j.status,
            )
            for j in qs
        ])

    def cancel_followup(
        self, request: CancelFollowupRequest
    ) -> CancelFollowupResponse:
        try:
            job = FollowupJob.objects.get(job_id=request.job_id)
        except FollowupJob.DoesNotExist:
            return CancelFollowupResponse(cancelled=False)

        if job.celery_task_id:
            try:
                from project.celery import app as celery_app
                celery_app.control.revoke(job.celery_task_id)
            except Exception as e:
                self.logger.warning("Could not revoke celery task: %s", e)

        job.status = FollowupJob.STATUS_CANCELLED
        job.save(update_fields=["status"])
        return CancelFollowupResponse(cancelled=True)
