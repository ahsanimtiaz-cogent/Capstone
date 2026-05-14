import discord
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Bot is online as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        user_text = message.content
        print(f"DM from {message.author}: {user_text}")

        reply = generate_reply(user_text)

        await message.channel.send(reply)


def generate_reply(text: str) -> str:
    text = text.lower()

    if "hello" in text:
        return "Hello! I received your message."

    if "help" in text:
        return "I am a bot. Send me anything and I will reply."

    return f"You said: {text}"


client.run(TOKEN)