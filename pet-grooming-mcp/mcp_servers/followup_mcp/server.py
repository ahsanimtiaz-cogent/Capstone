"""Followup MCP server: schedule_followup, list_followups, cancel_followup."""
from typing import Any

from fastmcp import FastMCP

from ..mcp_utils import handle_tool_call
from .client import FollowupMCPClient
from .models import (
    CancelFollowupRequest,
    CancelFollowupResponse,
    ListFollowupsRequest,
    ListFollowupsResponse,
    ScheduleFollowupRequest,
    ScheduleFollowupResponse,
)


DOMAIN_NAME = "followup"

DOMAIN_INSTRUCTIONS = """
This domain schedules and manages delayed DM follow-ups, backed by Celery + Postgres.

Key capabilities:
- schedule_followup: queue a DM to fire after delay_hours (default 24).
  Idempotent per lead: a second call while one is already pending returns
  duplicate=True without scheduling another.
- list_followups: read pending jobs (optionally scoped to a lead).
- cancel_followup: revoke a pending job.

Use schedule_followup after an objection or hesitation. Requires
`_lead_id` and `_discord_user_id` in request metadata.
""".strip()


def create_server() -> FastMCP:
    mcp = FastMCP(name=DOMAIN_NAME, instructions=DOMAIN_INSTRUCTIONS)

    @mcp.tool(tags={DOMAIN_NAME})
    async def schedule_followup(
        request: ScheduleFollowupRequest,
    ) -> ScheduleFollowupResponse | Any:
        """Queue a delayed DM follow-up. Idempotent per lead."""
        client = FollowupMCPClient(request)
        return await handle_tool_call(lambda: client.schedule_followup(request))

    @mcp.tool(tags={DOMAIN_NAME})
    async def list_followups(
        request: ListFollowupsRequest,
    ) -> ListFollowupsResponse | Any:
        """List pending followups, optionally scoped to a lead via _lead_id metadata."""
        client = FollowupMCPClient(request)
        return await handle_tool_call(lambda: client.list_followups(request))

    @mcp.tool(tags={DOMAIN_NAME})
    async def cancel_followup(
        request: CancelFollowupRequest,
    ) -> CancelFollowupResponse | Any:
        """Cancel a pending follow-up by job_id."""
        client = FollowupMCPClient(request)
        return await handle_tool_call(lambda: client.cancel_followup(request))

    return mcp
