# Discord Bot Setup and Server Invitation Guide

# Step 1: Create a Discord Application

Go to:

https://discord.com/developers/applications

- Click **New Application**
- Enter application name
- Click **Create**

---

# Step 2: Create Bot

Inside the application dashboard:

- Open the **Bot** tab
- Click **Add Bot**
- Confirm creation

---

# Step 3: Enable Required Bot Intents

Inside the Bot section enable:

- Presence Intent
- Server Members Intent
- Message Content Intent

Click **Save Changes**.

---

# Step 4: Copy Bot Token

Inside the Bot tab:

- Click **Reset Token** or **Copy Token**
- Save the token securely

Example:

```env
DISCORD_BOT_TOKEN=your_token_here
```

Never share the token publicly.

---

# Step 5: Add Bot to Discord Server

## Open OAuth2 URL Generator

From the left sidebar:

- Click **OAuth2**
- Click **URL Generator**

---

## Select OAuth Scopes

Under **Scopes**, enable:

```text
bot
```

Optional for slash commands:

```text
applications.commands
```

---

## Select Bot Permissions

Recommended minimum permissions:

- View Channels
- Send Messages
- Read Message History

Optional permissions:

- Manage Messages
- Embed Links
- Attach Files

---

## Copy Generated Invite URL

Discord will generate an authorization URL at the bottom.

Example:

```text
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2048&scope=bot
```

Copy this URL.

---

## Invite Bot to Server

- Open the generated URL in browser
- Select your Discord server
- Click **Authorize**
- Complete CAPTCHA if prompted

Requirements:

- You must have **Manage Server** permission
- Or be the server owner

---

# Step 6: Verify Bot Joined Server

Open your Discord server.

You should now see the bot in the member list.

Example:

```text
YourBotName
```

---

# Step 7: Install Python Dependencies

Install required packages:

```bash
pip install discord.py python-dotenv
```

---

# Step 8: Create `.env` File

Create a file named:

```bash
.env
```

Add:

```env
DISCORD_BOT_TOKEN=your_actual_token
```

---

# Step 9: Create `requirements.txt`

```txt
discord.py
python-dotenv
```

---

# Step 10: Create Bot Script

Create file:

```bash
bot.py
```

Add the following code:

```python
import os

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    print(f"{message.author}: {message.content}")

    await message.channel.send("Message received")


client.run(TOKEN)
```

---

# Step 11: Run the Bot

Start the bot:

```bash
python3 bot.py
```

Expected output:

```text
Logged in as YourBotName
```

---

# Step 12: Test the Bot

Send a message in your Discord server.

The bot should automatically reply:

```text
Message received
```

---

# Recommended Project Structure

```text
project/
│
├── bot.py
├── .env
├── requirements.txt
├── credentials.json
├── token.json
└── venv/
```

---

# Common Issues

## Bot Appears Offline

Check:

- Bot script is running
- Correct token is used
- `.env` file is loaded properly

---

## Cannot Add Bot to Server

Check:

- You have server management permissions
- Correct OAuth scopes are selected

---

## Bot Cannot Read Messages

Enable:

```text
Message Content Intent
```

From:

- Developer Portal
- Bot Section
- Privileged Gateway Intents

---

# Recommended Next Steps

You can now extend the bot to:

- Receive customer grooming requests
- Extract customer details
- Extract pet information
- Connect Gemini/OpenAI APIs
- Store leads in Google Sheets
- Book appointments into Google Calendar
- Send booking confirmations