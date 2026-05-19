from typing import List, Optional

from pydantic import BaseModel, Field

from ..base_client import BaseRequestModel


class ShowHoursRequest(BaseRequestModel):
    """Empty payload — just reads BrandConfig."""


class ShowHoursResponse(BaseModel):
    hours: str
    timezone: str


class FreeSlot(BaseModel):
    start_iso: str
    start_label: str
    end_label: str


class FetchFreeSlotsRequest(BaseRequestModel):
    day: str = Field(description="Target date in YYYY-MM-DD")
    service_id: str = Field(description="Service id to look up duration for")


class FetchFreeSlotsResponse(BaseModel):
    day: str
    duration_min: int
    slots: List[FreeSlot]
    error: Optional[str] = Field(
        default=None,
        description="Set when day is invalid (past, closed, malformed)."
    )


class BookAppointmentRequest(BaseRequestModel):
    day: str = Field(description="Date in YYYY-MM-DD")
    start_time: str = Field(description="Start time in HH:MM (24h)")
    service_id: str
    pet_name: str = Field(default="your pet")


class BookAppointmentResponse(BaseModel):
    booked: bool
    appt_id: Optional[str] = None
    calendar_event_id: Optional[str] = None
    scheduled_at_iso: Optional[str] = None
    duration_min: Optional[int] = None
    conflict_replacement_slots: List[FreeSlot] = Field(default_factory=list)
    error: Optional[str] = None
