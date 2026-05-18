from graph.state import GroomingState


def error_recovery_node(state: GroomingState):
    errors = state.get("errors") or []
    if errors:
        msg = "; ".join(errors[-2:])
        return {
            "reply": (
                f"Hmm, something went wrong: {msg}. "
                "Want to try again, or pick a different time?"
            )
        }
    return {
        "reply": (
            "Something didn't go through on my end. Could you try again? "
            "If it keeps happening, ask me about hours or services and I'll get you sorted."
        )
    }
