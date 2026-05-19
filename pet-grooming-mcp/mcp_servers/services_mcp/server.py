"""Services MCP server: list_services, select_service."""
from typing import Any

from fastmcp import FastMCP

from ..mcp_utils import handle_tool_call
from .client import ServicesMCPClient
from .models import (
    ListServicesRequest,
    ListServicesResponse,
    SelectServiceRequest,
    SelectServiceResponse,
)


DOMAIN_NAME = "services"

DOMAIN_INSTRUCTIONS = """
This domain handles the grooming service catalog.

Key capabilities:
- list_services: enumerate available services (Full Groom, Bath & Brush, etc.)
  with per-pet final pricing (weight bracket × breed modifier) and a recommendation.
  Use the recommended_service_id to populate the session for downstream
  affirmative-reply ("yes please") handling.
- select_service: fuzzy-match a user's free-text reply ("Full Groom", "the first one",
  "yes") to a concrete service. Returns the matched ServiceLine or matched=False.

Always pass the pet info (breed + weight especially) so pricing is correct.
""".strip()


def create_server() -> FastMCP:
    mcp = FastMCP(name=DOMAIN_NAME, instructions=DOMAIN_INSTRUCTIONS)

    @mcp.tool(tags={DOMAIN_NAME})
    async def list_services(request: ListServicesRequest) -> ListServicesResponse | Any:
        """List all grooming services with per-pet pricing and a recommendation."""
        client = ServicesMCPClient(request)
        return await handle_tool_call(lambda: client.list_services(request))

    @mcp.tool(tags={DOMAIN_NAME})
    async def select_service(request: SelectServiceRequest) -> SelectServiceResponse | Any:
        """Match a user's free-text reply to a concrete service."""
        client = ServicesMCPClient(request)
        return await handle_tool_call(lambda: client.select_service(request))

    return mcp
