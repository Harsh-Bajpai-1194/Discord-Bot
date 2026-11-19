# 🤖 Astragon Discord Bot

A 24×7 multi-purpose Discord bot built with Python (`discord.py`) and hosted on Render.

## ⚙️ Prerequisites & Setup
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file from `.env.example`:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
4. **Important Intents:**
   In the [Discord Developer Portal](https://discord.com/developers/applications) under **Bot > Privileged Gateway Intents**, enable:
   - ✅ **Message Content Intent** (for reading command messages and `#ai-chat` queries)
   - ✅ **Server Members Intent** (required for `on_member_join` welcome messages)

## 💬 Conversational Gemini AI (#ai-chat)
Astragon integrates Google's Gemini AI to provide conversational intelligence:
- **Dedicated Channel**: Create a text channel named `#ai-chat` (or customize via `AI_CHANNEL_NAME` in `.env`).
- **Context Window**: Maintains multi-turn conversational history across recent messages in `#ai-chat` so Gemini understands ongoing discussions.
- **Channel Isolation**: The bot only triggers AI responses in `#ai-chat`, keeping all other server channels spam-free.
- **Smart Formatting**: Automatically chunks responses longer than Discord's 2000-character limit without cutting words or paragraphs.

## 📌 Commands
Commands work as both **Slash Commands** (`/`) and **Prefix Commands** (`!`):
- `/ping` (or `!ping`) - Check bot response latency and API heartbeat
- `/hello` (or `!hello`) - Sends a friendly greeting
- `/help` (or `!help`) - Displays interactive command embed

## 🧪 Running Tests
Unit tests use Python's built-in `unittest.mock` to test without requiring live Discord tokens or API keys:
```bash
pytest
```
