# Discord Bot Setup Guide (Python)

## Step 1: Create a Discord Application

Go to:

https://discord.com/developers/applications

---

## Step 2: Create New Application

- Click **New Application**
- Enter application name
- Click **Create**

---

## Step 3: Create Bot

Inside the application dashboard:

- Open the **Bot** tab
- Click **Add Bot**
- Confirm creation

---

## Step 4: Enable Required Bot Intents

Inside the Bot section enable:

- Presence Intent
- Server Members Intent
- Message Content Intent

Save changes.

---

## Step 5: Copy Bot Token

Inside the Bot tab:

- Click **Reset Token** or **Copy Token**
- Save the token securely

Example:

```env
DISCORD_BOT_TOKEN=your_token_here