"""Completion dispatch — direct port of lang-graph/graph/routers/completion_router.py."""
from typing import Any, Dict

from .session_service import is_qualified


def completion_router(session: Dict[str, Any]) -> str:
    return "qualified" if is_qualified(session) else "incomplete"
