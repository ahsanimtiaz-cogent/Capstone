"""LLM availability detection.

Each agent calls `llm_enabled()` to decide between PydanticAI and the
deterministic fallback. Settings are read via Django to keep config in
one place.
"""
from __future__ import annotations

from typing import Optional


def llm_enabled() -> bool:
    try:
        from django.conf import settings
        return bool(getattr(settings, "OPENROUTER_API_KEY", "") or "")
    except Exception:
        return False


def get_model_id() -> str:
    try:
        from django.conf import settings
        return getattr(settings, "OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    except Exception:
        return "anthropic/claude-3.5-sonnet"


def build_agent(result_type, system_prompt: str) -> Optional[object]:
    """Construct a PydanticAI Agent if the SDK + API key are available; else None."""
    if not llm_enabled():
        return None
    try:
        from pydantic_ai import Agent
        # PydanticAI accepts `openrouter:<model>` model strings. Newer versions use
        # `output_type=`; older ones use `result_type=`.
        try:
            return Agent(
                model=f"openrouter:{get_model_id()}",
                output_type=result_type,
                system_prompt=system_prompt,
            )
        except TypeError:
            return Agent(
                model=f"openrouter:{get_model_id()}",
                result_type=result_type,
                system_prompt=system_prompt,
            )
    except Exception:
        return None


def unwrap(result):
    """Read the structured payload off a PydanticAI run result.

    Recent versions expose `result.output`; older ones use `result.data`.
    """
    if hasattr(result, "output"):
        return result.output
    return result.data
