"""Headless Discord sender used by Celery workers to deliver follow-ups.

The web/bot service can stay running long-lived. The Celery worker is a
separate process — when a follow-up fires it spins up a short-lived
discord.Client, sends the DM, and shuts down. Cheap enough for the
expected (low) followup volume.
"""
import asyncio
import logging

import discord

logger = logging.getLogger(__name__)


class DiscordSender:
    def __init__(self, token: str):
        self._token = token

    async def send(self, discord_user_id: str, message: str) -> None:
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        async def runner():
            try:
                user = await client.fetch_user(int(discord_user_id))
                await user.send(message)
            except Exception as e:
                logger.warning("Could not DM user %s: %s", discord_user_id, e)
            finally:
                await client.close()

        @client.event
        async def on_ready():
            asyncio.create_task(runner())

        await client.start(self._token)
