"""Discord bot entry point: `python -m project.grooming.bot.runner`.

Replaces lang-graph/main.py. Boots Django, instantiates the Coordinator,
attaches Discord handlers, and runs the client.
"""
import logging
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parents[3]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

from project.grooming.bot.client import build_client  # noqa: E402
from project.grooming.bot.handlers import attach_handlers  # noqa: E402
from project.grooming.orchestrator.coordinator import Coordinator  # noqa: E402


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    token = settings.DISCORD_TOKEN
    if not token:
        raise SystemExit("DISCORD_TOKEN is not set in the environment.")

    coordinator = Coordinator()
    client = build_client()
    attach_handlers(client, coordinator)
    client.run(token)


if __name__ == "__main__":
    main()
