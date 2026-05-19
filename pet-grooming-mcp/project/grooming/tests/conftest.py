"""Pytest fixtures: reset MCP integration singletons + suppress Celery eager exec."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mcp_servers import mcp_utils

from .fakes import FakeCalendarService, FakeSheetsRepo


@pytest.fixture
def integrations(db):  # `db` activates Django's test DB
    sheets = FakeSheetsRepo()
    calendar = FakeCalendarService()
    mcp_utils.set_test_integrations(sheets=sheets, calendar=calendar)

    # Suppress eager Celery execution of `send_followup`. The test only cares
    # that the FollowupJob row is written; actually invoking the task inside
    # the open SQLite transaction (CELERY_TASK_ALWAYS_EAGER=True in test
    # settings) deadlocks the connection.
    with patch("project.grooming.tasks.send_followup.apply_async",
               return_value=SimpleNamespace(id="celery-test-id")):
        yield sheets, calendar

    mcp_utils._sheets_singleton = None  # noqa: SLF001
    mcp_utils._calendar_singleton = None  # noqa: SLF001
