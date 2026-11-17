# 🤖 Astragon Discord Bot

A 24×7 multi-purpose Discord bot built with Python (`discord.py`) and hosted on Render.

## ⚙️ Prerequisites & Setup
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your configuration:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   OPENWEATHER_API_KEY=your_openweather_api_key_optional
   ```
   *(Note: `OPENWEATHER_API_KEY` is optional; if omitted, `/weather` automatically falls back to `wttr.in`).*

4. **Important Intents & Permissions:**
   In the [Discord Developer Portal](https://discord.com/developers/applications):
   - Under **Bot > Privileged Gateway Intents**, enable:
     - ✅ **Message Content Intent** (for reading command messages)
     - ✅ **Server Members Intent** (required for `on_member_join` welcome messages)
   - Under **OAuth2 > URL Generator**, ensure the bot invite URL has:
     - Scopes: `bot`, `applications.commands`

## 📌 Commands
Commands work as both **Slash Commands** (`/`) and **Prefix Commands** (`!`):

### General
- `/ping` (or `!ping`) - Check bot response latency
- `/hello` (or `!hello`) - Friendly greeting
- `/help` (or `!help`) - Display interactive command embed

### Fun & Utility APIs
- `/joke` (or `!joke`) - Tells a random safe joke (via JokeAPI)
- `/fact` (or `!fact`) - Shares a random interesting fact (via UselessFacts)
- `/weather <city>` (or `!weather <city>`) - Fetches current weather for a city
