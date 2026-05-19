"""External-service adapters (Google Sheets, Google Calendar, fuzzy matching).

Ported near-verbatim from `lang-graph/services/`. Sheets and Calendar
remain the system of record for leads, services, appointments —
only sessions and followups moved to Postgres.
"""
