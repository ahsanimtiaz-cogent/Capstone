"""Grooming MCP servers (FastMCP).

Five domain sub-servers composed into one unified server:
- qualification_mcp  — qualify_lead, get_qualification_status
- services_mcp       — list_services, select_service, recommend_service
- booking_mcp        — show_hours, fetch_free_slots, book_appointment
- followup_mcp       — schedule_followup, list_followups, cancel_followup
- knowledge_mcp      — get_brand_config, faq_context

Entry point: `python -m mcp_servers.grooming_mcp_server` (port 8010).
"""
