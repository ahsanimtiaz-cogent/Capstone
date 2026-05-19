"""Discord message handlers.

Ported from lang-graph/bot/handlers.py. Swaps the LangGraph invocation
for `Coordinator.handle_message()`. Session persistence happens inside
the Coordinator (Postgres) — there's no JSON file to read/write here.
"""
import asyncio
import logging

import discord

from project.grooming.orchestrator.coordinator import Coordinator

logger = logging.getLogger(__name__)


def attach_handlers(client: discord.Client, coordinator: Coordinator):
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

        display_name = str(message.author.display_name or "")

        try:
            reply = await asyncio.to_thread(
                coordinator.handle_message, user_id, user_message, display_name,
            )
        except Exception:
            logger.exception("Coordinator failed for user %s", user_id)
            await message.channel.send(
                "Sorry — something went wrong on my end. Could you try again?"
            )
            return

        if not reply:
            reply = "Got it."

        # Discord caps messages at 2000 chars
        for chunk in (reply[i:i + 1900] for i in range(0, len(reply), 1900)):
            await message.channel.send(chunk)
