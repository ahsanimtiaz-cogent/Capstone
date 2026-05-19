import discord


def build_client() -> discord.Client:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.dm_messages = True
    return discord.Client(intents=intents)
