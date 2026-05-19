"""Deterministic FSM orchestrator — ports the LangGraph routers 1:1.

Public surface:
- Coordinator.handle_message(user_id, text, display_name) -> reply
- SessionService for session CRUD
- Stages / Intents enums + empty_session() helper
"""
