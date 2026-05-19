"""Booking MCP server: show_hours, fetch_free_slots, book_appointment."""
from typing import Any

from fastmcp import FastMCP

from ..mcp_utils import handle_tool_call
from .client import BookingMCPClient
from .models import (
    BookAppointmentRequest,
    BookAppointmentResponse,
    FetchFreeSlotsRequest,
    FetchFreeSlotsResponse,
    ShowHoursRequest,
    ShowHoursResponse,
)


DOMAIN_NAME = "booking"

DOMAIN_INSTRUCTIONS = """
This domain handles appointment booking against Google Calendar + Sheets.

Key capabilities:
- show_hours: read BrandConfig's open hours + timezone.
- fetch_free_slots: given a day (YYYY-MM-DD) and service_id, return all
  30-minute-step starting times whose [start, start+duration) is free.
  Returns an `error` when the day is malformed/past/closed.
- book_appointment: transactional — creates a Calendar event, appends an
  Appointments row, flips lead status to 'booked'. Rolls back the calendar
  event if the sheet write fails. Returns `error='slot_taken'` with fresh
  alternatives if the slot was claimed between fetch and book.

Always pass `_lead_id` in metadata so same-lead overlap is enforced and
the lead status is updated on success.
""".strip()


def create_server() -> FastMCP:
    mcp = FastMCP(name=DOMAIN_NAME, instructions=DOMAIN_INSTRUCTIONS)

    @mcp.tool(tags={DOMAIN_NAME})
    async def show_hours(request: ShowHoursRequest) -> ShowHoursResponse | Any:
        """Return business hours + timezone."""
        client = BookingMCPClient(request)
        return await handle_tool_call(lambda: client.show_hours(request))

    @mcp.tool(tags={DOMAIN_NAME})
    async def fetch_free_slots(request: FetchFreeSlotsRequest) -> FetchFreeSlotsResponse | Any:
        """Return the free 30-min-step start times on `day` for the given service."""
        client = BookingMCPClient(request)
        return await handle_tool_call(lambda: client.fetch_free_slots(request))

    @mcp.tool(tags={DOMAIN_NAME})
    async def book_appointment(request: BookAppointmentRequest) -> BookAppointmentResponse | Any:
        """Create Calendar event + Appointments row transactionally; flip lead to 'booked'."""
        client = BookingMCPClient(request)
        return await handle_tool_call(lambda: client.book_appointment(request))

    return mcp
