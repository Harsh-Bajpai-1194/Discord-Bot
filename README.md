# 🤖 Astragon Discord Bot

A 24×7 multi-purpose Discord bot built with Python (`discord.py`) and hosted on Render.

## ⚙️ Prerequisites & Setup
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your bot token:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```
4. **Important Intents & Permissions:**
   In the [Discord Developer Portal](https://discord.com/developers/applications):
   - Under **Bot > Privileged Gateway Intents**, enable:
     - ✅ **Message Content Intent** (for reading command messages)
     - ✅ **Server Members Intent** (required for `on_member_join` welcome messages)
   - Under **OAuth2 > URL Generator**, ensure the bot invite URL has:
     - Scopes: `bot`, `applications.commands`
     - Bot Permissions: `Kick Members`, `Ban Members`, `Send Messages`, `Embed Links`, etc.

## 📌 Commands
Commands work as both **Slash Commands** (`/`) and **Prefix Commands** (`!`):

### General
- `/ping` (or `!ping`) - Check bot response latency
- `/hello` (or `!hello`) - Friendly greeting
- `/help` (or `!help`) - Display interactive command embed

### Moderation
- `/kick @user [reason]` (or `!kick`) - Kick a member from the server
- `/ban @user [reason]` (or `!ban`) - Ban a member from the server
