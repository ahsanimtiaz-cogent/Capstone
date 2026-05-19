"""Knowledge MCP server: get_brand_config (FAQ + objection grounding)."""
from typing import Any

from fastmcp import FastMCP

from ..mcp_utils import handle_tool_call
from .client import KnowledgeMCPClient
from .models import GetBrandConfigRequest, GetBrandConfigResponse


DOMAIN_NAME = "knowledge"

DOMAIN_INSTRUCTIONS = """
This domain exposes brand-level facts the FAQ and Objection agents need
to ground their responses (hours, location, timezone, objection snippets,
upsells).

Key capability:
- get_brand_config: return the full BrandConfig row from Sheets.

Call this once before composing an FAQ or objection reply, then let the
PydanticAI agent paraphrase the facts.
""".strip()


def create_server() -> FastMCP:
    mcp = FastMCP(name=DOMAIN_NAME, instructions=DOMAIN_INSTRUCTIONS)

    @mcp.tool(tags={DOMAIN_NAME})
    async def get_brand_config(
        request: GetBrandConfigRequest,
    ) -> GetBrandConfigResponse | Any:
        """Return business hours, location, timezone, and objection snippets."""
        client = KnowledgeMCPClient(request)
        return await handle_tool_call(lambda: client.get_brand_config(request))

    return mcp
