from typing import List, Optional

from pydantic import BaseModel, Field

from ..base_client import BaseRequestModel


class ScheduleFollowupRequest(BaseRequestModel):
    message: str = Field(
        default="Hi! Just checking back about your grooming appointment.",
        description="DM body to send when the followup fires.",
    )
    delay_hours: float = Field(
        default=24.0, ge=0.0,
        description="Hours to wait before firing.",
    )


class ScheduleFollowupResponse(BaseModel):
    scheduled: bool
    job_id: Optional[str] = None
    duplicate: bool = False
    error: Optional[str] = None


class ListFollowupsRequest(BaseRequestModel):
    """No payload — implicitly scoped to `_lead_id` if provided."""


class FollowupJobOut(BaseModel):
    job_id: str
    lead_id: str
    discord_user_id: str
    message: str
    send_at_iso: str
    status: str


class ListFollowupsResponse(BaseModel):
    jobs: List[FollowupJobOut]


class CancelFollowupRequest(BaseRequestModel):
    job_id: str


class CancelFollowupResponse(BaseModel):
    cancelled: bool
