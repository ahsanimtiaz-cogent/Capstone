from graph.state import GroomingState
from graph.nodes.session import is_qualified


def completion_router(state: GroomingState) -> str:
    return "qualified" if is_qualified(state.get("session", {})) else "incomplete"
