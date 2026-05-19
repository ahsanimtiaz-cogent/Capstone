import asyncio
import json
import logging
import os
from typing import Any, Dict

import discord

from graph.state import GroomingState, empty_session
from services.sheets_service import SheetsRepo

logger = logging.getLogger(__name__)


def _load_sessions(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_sessions(path: str, sessions: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, default=str)


def attach_handlers(client: discord.Client, graph, sheets: SheetsRepo,
                    sessions_path: str):
    sessions = _load_sessions(sessions_path)

    @client.event
    async def on_ready():
        logger.info("Discord bot connected as %s", client.user)

    @client.event
    async def on_message(message: discord.Message):
        if message.author == client.user:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return

        user_id = str(message.author.id)
        user_message = (message.content or "").strip()
        if not user_message:
            return

        session = sessions.get(user_id) or empty_session()

        # Ensure a Sheets lead exists for this user
        if not session.get("lead_id"):
            try:
                existing = sheets.get_lead_by_discord_id(user_id)
                if existing:
                    session["lead_id"] = existing["lead_id"]
                    session["name"] = existing.get("name") or session.get("name", "")
                    session["phone"] = existing.get("phone") or session.get("phone", "")
                    session["city"] = existing.get("city") or session.get("city", "")
                else:
                    created = sheets.create_lead(
                        discord_user_id=user_id,
                        name=str(message.author.display_name or ""),
                    )
                    session["lead_id"] = created["lead_id"]
            except Exception as e:
                logger.exception("Could not initialize lead: %s", e)
                await message.channel.send(
                    "I'm having trouble accessing our records. Please try again in a moment."
                )
                return

        state: GroomingState = {
            "user_id": user_id,
            "user_message": user_message,
            "session": session,
            "intent": "",
            "extracted_data": {},
            "selected_service": {},
            "available_slots": [],
            "booking_day": session.get("booking_day", ""),
            "booking_time": "",
            "booking_confirmed": False,
            "qualified": False,
            "reply": "",
            "errors": [],
        }

        try:
            result: GroomingState = await asyncio.to_thread(graph.invoke, state)
        except Exception as e:
            logger.exception("Graph invocation failed: %s", e)
            await message.channel.send(
                "Sorry — something went wrong on my end. Could you try again?"
            )
            return

        # Persist session
        sessions[user_id] = result.get("session", session)
        try:
            _save_sessions(sessions_path, sessions)
        except Exception as e:
            logger.warning("Could not persist sessions: %s", e)

        reply = result.get("reply") or "Got it."
        # Discord caps messages at 2000 chars
        for chunk in (reply[i:i+1900] for i in range(0, len(reply), 1900)):
            await message.channel.send(chunk)

    async def send_dm(discord_user_id: str, message: str) -> None:
        try:
            user = await client.fetch_user(int(discord_user_id))
            await user.send(message)
        except Exception as e:
            logger.warning("Could not DM user %s: %s", discord_user_id, e)

    return send_dm
