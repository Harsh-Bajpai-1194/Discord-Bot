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
     - Bot Permissions:
       - `Send Messages` & `Send Messages in Threads` (channel & thread messaging)
       - `Embed Links` (embed responses & purge confirmations)
       - `Read Message History` (required for `/purge`, `/clear`)
       - `Manage Messages` (required for `/purge`, `/clear`)
       - `Kick Members` (required for `/kick`)
       - `Ban Members` (required for `/ban`)
       - `Moderate Members` (required for `/timeout`, `/untimeout`)

## 📌 Commands
Commands work as both **Slash Commands** (`/`) and **Prefix Commands** (`!`):

### General
- `/ping` (or `!ping`) - Check bot response latency
- `/hello` (or `!hello`) - Friendly greeting
- `/help` (or `!help`) - Display interactive command embed

### Moderation
- `/kick <user> [reason]` (or `!kick @user [reason]`) - Kick a member from the server (Requires Kick Members permission)
- `/ban <user> [reason]` (or `!ban @user [reason]`) - Ban a member from the server while preserving message history (Requires Ban Members permission)
- `/timeout <user> [duration] [reason]` (or `!timeout @user [duration] [reason]`) - Time out a member (default: `10m`, formats: `10s`, `10m`, `1h`, `1d`, max: 28 days) (Requires Moderate Members permission)
- `/untimeout <user> [reason]` (or `!untimeout @user [reason]`) - Remove timeout from a member (Requires Moderate Members permission)
- `/purge <amount>` (or `!purge <amount>`, `!clear <amount>`) - Bulk delete recent messages (1-100) (Requires Manage Messages permission)
