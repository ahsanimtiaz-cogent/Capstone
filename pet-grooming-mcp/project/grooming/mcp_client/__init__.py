"""In-process MCP client used by the Django coordinator.

The MCP server (`mcp_servers/grooming_mcp_server.py`) is the public surface
for external agents (Claude Desktop, other MCP-aware clients). The Django
orchestrator calls the same domain `*Client` classes directly here — same
behavior, no network hop, easier to test.

If you want the orchestrator to round-trip through the running MCP server
(e.g., to validate the wire schema), wire an HTTP client and swap the
implementation behind this facade. The signatures stay the same.
"""
from .client import MCPClient

__all__ = ("MCPClient",)
