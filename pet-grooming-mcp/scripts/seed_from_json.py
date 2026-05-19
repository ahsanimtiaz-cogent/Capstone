"""One-shot migration: copy lang-graph/storage/{sessions,followups}.json into Postgres.

Usage:
    python manage.py shell -c "exec(open('scripts/seed_from_json.py').read())"

Or via Django management command path (preferred):
    python scripts/seed_from_json.py
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import django

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.utils import timezone  # noqa: E402

from project.grooming.models import ChatSession, FollowupJob  # noqa: E402


LANG_GRAPH_STORAGE = Path("/Users/cogent/Ai Training/Capstone/lang-graph/storage")


def seed_sessions() -> int:
    path = LANG_GRAPH_STORAGE / "sessions.json"
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    n = 0
    for discord_user_id, payload in data.items():
        ChatSession.objects.update_or_create(
            discord_user_id=str(discord_user_id),
            defaults={"payload": payload, "display_name": payload.get("name", "")},
        )
        n += 1
    return n


def seed_followups() -> int:
    path = LANG_GRAPH_STORAGE / "followups.json"
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    n = 0
    for job in jobs:
        try:
            send_at = datetime.fromisoformat(job["send_at_iso"])
        except (KeyError, ValueError):
            continue
        if send_at.tzinfo is None:
            send_at = timezone.make_aware(send_at, timezone.utc)
        FollowupJob.objects.update_or_create(
            job_id=job["job_id"],
            defaults={
                "lead_id": job.get("lead_id", ""),
                "discord_user_id": job.get("discord_user_id", ""),
                "message": job.get("message", ""),
                "send_at": send_at,
                "status": FollowupJob.STATUS_PENDING,
            },
        )
        n += 1
    return n


if __name__ == "__main__":
    sessions = seed_sessions()
    followups = seed_followups()
    print(f"Seeded {sessions} session(s) and {followups} followup(s).")
