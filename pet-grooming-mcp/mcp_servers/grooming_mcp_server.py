"""Unified Grooming MCP Server.

Composes the five domain sub-servers (qualification, services, booking,
followup, knowledge) into one FastMCP endpoint using `import_server` with
per-domain prefixes — so tool names look like `booking_fetch_free_slots`,
`qualification_qualify_lead`, etc. This is the pattern from
[MCP Template guide/src/chat/mcp_servers/chughtai_lab_server.py].

Run directly:
    python -m mcp_servers.grooming_mcp_server
"""
import logging
import os
import sys
from pathlib import Path
from textwrap import dedent

# Ensure Django settings + project paths are configured before any domain
# clients that touch Django models (e.g. followup_mcp) are imported.
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from fastmcp import FastMCP  # noqa: E402

from .booking_mcp.server import (  # noqa: E402
    DOMAIN_INSTRUCTIONS as BOOKING_INSTRUCTIONS,
    DOMAIN_NAME as BOOKING_NAME,
    create_server as create_booking_server,
)
from .followup_mcp.server import (  # noqa: E402
    DOMAIN_INSTRUCTIONS as FOLLOWUP_INSTRUCTIONS,
    DOMAIN_NAME as FOLLOWUP_NAME,
    create_server as create_followup_server,
)
from .knowledge_mcp.server import (  # noqa: E402
    DOMAIN_INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS,
    DOMAIN_NAME as KNOWLEDGE_NAME,
    create_server as create_knowledge_server,
)
from .qualification_mcp.server import (  # noqa: E402
    DOMAIN_INSTRUCTIONS as QUALIFICATION_INSTRUCTIONS,
    DOMAIN_NAME as QUALIFICATION_NAME,
    create_server as create_qualification_server,
)
from .services_mcp.server import (  # noqa: E402
    DOMAIN_INSTRUCTIONS as SERVICES_INSTRUCTIONS,
    DOMAIN_NAME as SERVICES_NAME,
    create_server as create_services_server,
)

logger = logging.getLogger(__name__)

UNIFIED_SERVER_NAME = "pet grooming bot"


def build_unified_instructions() -> str:
    header = dedent(
        f"""
        You are the "{UNIFIED_SERVER_NAME}" MCP server. You expose tools from
        five domains, each prefixed by the domain name:

        - {QUALIFICATION_NAME}_*  → qualify a lead, read qualification status
        - {SERVICES_NAME}_*       → list/recommend services, select_service
        - {BOOKING_NAME}_*        → show hours, fetch free slots, book appointment
        - {FOLLOWUP_NAME}_*       → schedule/list/cancel delayed DM follow-ups
        - {KNOWLEDGE_NAME}_*      → read BrandConfig facts (hours, location, snippets)

        The orchestrator (Django coordinator) decides which tool to call
        based on the user's intent and the lead's current stage; you
        execute the call against Google Sheets/Calendar and Postgres.
        """
    ).strip()

    domain_blocks = [
        (QUALIFICATION_NAME, QUALIFICATION_INSTRUCTIONS),
        (SERVICES_NAME, SERVICES_INSTRUCTIONS),
        (BOOKING_NAME, BOOKING_INSTRUCTIONS),
        (FOLLOWUP_NAME, FOLLOWUP_INSTRUCTIONS),
        (KNOWLEDGE_NAME, KNOWLEDGE_INSTRUCTIONS),
    ]
    merged = "\n\n".join(
        f"[Domain: {name}]\n{instr.strip()}" for name, instr in domain_blocks
    )
    return header + "\n\n" + merged


mcp = FastMCP(name=UNIFIED_SERVER_NAME, instructions=build_unified_instructions())


def setup() -> None:
    # `mount` is the current FastMCP API (replaces deprecated `import_server`).
    # In recent fastmcp it's sync and takes `namespace=` instead of `prefix=`.
    mcp.mount(create_qualification_server(), namespace=QUALIFICATION_NAME)
    mcp.mount(create_services_server(), namespace=SERVICES_NAME)
    mcp.mount(create_booking_server(), namespace=BOOKING_NAME)
    mcp.mount(create_followup_server(), namespace=FOLLOWUP_NAME)
    mcp.mount(create_knowledge_server(), namespace=KNOWLEDGE_NAME)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    setup()
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8010"))
    logger.info("Starting unified grooming MCP server on %s:%s", host, port)
    # FastMCP runs its own ASGI server when given a transport name.
    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()
