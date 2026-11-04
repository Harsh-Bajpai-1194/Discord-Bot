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
4. **Important Intents:**
   In the [Discord Developer Portal](https://discord.com/developers/applications) under **Bot > Privileged Gateway Intents**, enable:
   - ✅ **Message Content Intent** (for reading command messages)
   - ✅ **Server Members Intent** (required for `on_member_join` welcome messages)

## 📌 Commands
- `!ping` - Check bot response latency
- `!hello` - Friendly greeting
- `!help` - Display interactive command embed