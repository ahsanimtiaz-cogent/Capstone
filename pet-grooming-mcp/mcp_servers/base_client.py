"""Shared base classes for MCP request models and clients.

Modeled on `MCP Template guide/src/chat/mcp_servers/base_client.py`,
but adapted to wrap in-process integrations (Sheets, Calendar) instead
of remote HTTP services.
"""
import logging
from abc import ABC
from typing import Any

from pydantic import BaseModel, model_validator


class BaseRequestModel(BaseModel):
    """Base request model: allows internal `_*` metadata fields, rejects unknown ones.

    The orchestrator injects `_lead_id`, `_discord_user_id`, etc. at call time so
    tool implementations have the operational context they need without leaking
    those fields into the tool's public schema.
    """

    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def allow_internal_metadata(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        invalid = [k for k in data.keys()
                   if k not in cls.model_fields and not k.startswith("_")]

        if invalid:
            valid = ", ".join(f"'{f}'" for f in cls.model_fields.keys())
            invalid_str = ", ".join(f"'{f}'" for f in invalid)
            raise ValueError(
                f"Invalid field(s): {invalid_str}. Valid fields: {valid}."
            )
        return data


class BaseMCPClient(ABC):
    """Common metadata extraction for all domain clients."""

    def __init__(self, request: BaseRequestModel):
        self.lead_id: str = getattr(request, "_lead_id", "") or ""
        self.discord_user_id: str = getattr(request, "_discord_user_id", "") or ""
        self.session_id: str = getattr(request, "_session_id", "") or ""
        self.logger = logging.getLogger(self.__class__.__module__)
