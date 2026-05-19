import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


SendFn = Callable[[str, str], Awaitable[None]]


class ReminderService:
    """APScheduler-based follow-up scheduler with disk persistence for rehydration."""

    def __init__(self, store_path: str, send_fn: SendFn):
        self._store_path = store_path
        self._send_fn = send_fn
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self._scheduler.start()
        self._rehydrate()

    # ---- public API --------------------------------------------------------

    def schedule_followup(self, lead_id: str, discord_user_id: str,
                          message: str, delay_hours: float = 24.0) -> str:
        send_at = datetime.utcnow() + timedelta(hours=delay_hours)
        job_id = f"fu_{uuid.uuid4().hex[:10]}"
        self._add_job(job_id, lead_id, discord_user_id, message, send_at)
        self._persist_job(job_id, lead_id, discord_user_id, message, send_at)
        logger.info("Scheduled follow-up %s for lead=%s at %s", job_id, lead_id, send_at)
        return job_id

    def cancel_followup(self, job_id: str) -> None:
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass
        self._remove_persisted_job(job_id)

    def list_pending(self) -> List[Dict[str, str]]:
        return self._load_jobs()

    # ---- internals --------------------------------------------------------

    def _add_job(self, job_id: str, lead_id: str, discord_user_id: str,
                 message: str, send_at: datetime) -> None:
        self._scheduler.add_job(
            self._fire,
            trigger="date",
            run_date=send_at,
            id=job_id,
            kwargs={
                "job_id": job_id,
                "lead_id": lead_id,
                "discord_user_id": discord_user_id,
                "message": message,
            },
            replace_existing=True,
        )

    async def _fire(self, job_id: str, lead_id: str, discord_user_id: str, message: str) -> None:
        try:
            await self._send_fn(discord_user_id, message)
            logger.info("Follow-up sent for lead=%s (job=%s)", lead_id, job_id)
        except Exception as e:
            logger.exception("Follow-up failed for lead=%s: %s", lead_id, e)
        finally:
            self._remove_persisted_job(job_id)

    def _persist_job(self, job_id: str, lead_id: str, discord_user_id: str,
                     message: str, send_at: datetime) -> None:
        jobs = self._load_jobs()
        jobs = [j for j in jobs if j["job_id"] != job_id]
        jobs.append({
            "job_id": job_id,
            "lead_id": lead_id,
            "discord_user_id": discord_user_id,
            "message": message,
            "send_at_iso": send_at.isoformat(),
        })
        self._save_jobs(jobs)

    def _remove_persisted_job(self, job_id: str) -> None:
        jobs = self._load_jobs()
        jobs = [j for j in jobs if j["job_id"] != job_id]
        self._save_jobs(jobs)

    def _load_jobs(self) -> List[Dict[str, str]]:
        if not os.path.exists(self._store_path):
            return []
        try:
            with open(self._store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _save_jobs(self, jobs: List[Dict[str, str]]) -> None:
        os.makedirs(os.path.dirname(self._store_path) or ".", exist_ok=True)
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2)

    def _rehydrate(self) -> None:
        jobs = self._load_jobs()
        now = datetime.utcnow()
        live: List[Dict[str, str]] = []
        for j in jobs:
            try:
                send_at = datetime.fromisoformat(j["send_at_iso"])
            except (KeyError, ValueError):
                continue
            if send_at <= now:
                # past-due: fire on next loop tick
                asyncio.get_event_loop().create_task(
                    self._send_fn(j["discord_user_id"], j["message"])
                )
                continue
            self._add_job(j["job_id"], j["lead_id"], j["discord_user_id"],
                          j["message"], send_at)
            live.append(j)
        self._save_jobs(live)
        if live:
            logger.info("Rehydrated %s pending follow-up(s)", len(live))
