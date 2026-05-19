"""Qualification MCP server: qualify_lead, get_qualification_status."""
from typing import Any

from fastmcp import FastMCP

from ..mcp_utils import handle_tool_call
from .client import QualificationMCPClient
from .models import (
    GetQualificationStatusRequest,
    GetQualificationStatusResponse,
    QualifyLeadRequest,
    QualifyLeadResponse,
)


DOMAIN_NAME = "qualification"

DOMAIN_INSTRUCTIONS = """
This domain handles lead qualification for the pet-grooming bot.

Key capabilities:
- qualify_lead: persist customer + pet info to the source-of-truth Sheets,
  flip the lead's status to 'qualified', and create a Pets row idempotently
  (same name + breed → no duplicate).
- get_qualification_status: read the current Sheets status + pet snapshot
  for a lead. Use this when you need to know whether qualification is complete.

Call qualify_lead only AFTER the orchestrator has confirmed all required
customer/pet fields are present (phone valid; pet name/breed/weight/age/coat).
""".strip()


def create_server() -> FastMCP:
    mcp = FastMCP(name=DOMAIN_NAME, instructions=DOMAIN_INSTRUCTIONS)

    @mcp.tool(tags={DOMAIN_NAME})
    async def qualify_lead(request: QualifyLeadRequest) -> QualifyLeadResponse | Any:
        """Mark the lead as qualified, append a Pets row, sync contact fields to Sheets.

        Requires `_lead_id` in request metadata.
        """
        client = QualificationMCPClient(request)
        return await handle_tool_call(lambda: client.qualify_lead(request))

    @mcp.tool(tags={DOMAIN_NAME})
    async def get_qualification_status(
        request: GetQualificationStatusRequest,
    ) -> GetQualificationStatusResponse | Any:
        """Return current Sheets status + saved pet snapshot for the lead."""
        client = QualificationMCPClient(request)
        return await handle_tool_call(lambda: client.get_qualification_status(request))

    return mcp
