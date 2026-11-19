import discord
from discord.ext import commands
import os
import warnings
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()  # loads .env file

# ────────────────── Keep-alive server (required for Render Web Service) ──────────────────────
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_server():
    try:
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Keep-alive server error: {e}")

def keep_alive():
    """Starts the Flask keep-alive server in a background daemon thread."""
    thread = Thread(target=run_server, daemon=True)
    thread.start()
    return thread
# ───────────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # For member join/leave events

class AstragonBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        """Sync slash commands with Discord upon bot startup."""
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

bot = AstragonBot()

# ── Gemini AI Configuration & Helpers ─────────────────────────────────────
AI_CHANNEL_NAME = os.getenv("AI_CHANNEL_NAME", "ai-chat").lower()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_HISTORY_LIMIT = int(os.getenv("GEMINI_HISTORY_LIMIT", "10"))

_cached_model = None

def get_ai_model():
    """Returns an initialized Gemini GenerativeModel or None if unconfigured/unavailable."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai
        warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
        genai.configure(api_key=api_key)
        _cached_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        return _cached_model
    except Exception as e:
        print(f"⚠️ Failed to initialize Gemini AI model: {e}")
        return None


def split_message(text: str, max_length: int = 2000) -> list[str]:
    """Splits a response message into chunks <= max_length characters to comply with Discord limits."""
    if not text:
        return []
    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text
    while len(remaining) > max_length:
        # Prefer splitting at paragraph breaks, then line breaks, then spaces
        split_idx = remaining.rfind("\n\n", 0, max_length)
        if split_idx != -1:
            chunk = remaining[:split_idx]
            remaining = remaining[split_idx + 2:]
        else:
            split_idx = remaining.rfind("\n", 0, max_length)
            if split_idx != -1:
                chunk = remaining[:split_idx]
                remaining = remaining[split_idx + 1:]
            else:
                split_idx = remaining.rfind(" ", 0, max_length)
                if split_idx != -1:
                    chunk = remaining[:split_idx]
                    remaining = remaining[split_idx + 1:]
                else:
                    chunk = remaining[:max_length]
                    remaining = remaining[max_length:]

        if chunk:
            chunks.append(chunk)

    if remaining:
        chunks.append(remaining)

    return chunks


async def build_gemini_history(channel, current_message, limit: int = 10) -> tuple[list[dict], str]:
    """
    Fetches recent messages from the channel and structures them for Gemini ChatSession history.
    Ensures turns in history strictly alternate and begin with 'user' and end with 'model'.
    Preserves any trailing unanswered user text so it can be combined into the next prompt.
    """
    try:
        raw_messages = [msg async for msg in channel.history(limit=limit, before=current_message)]
        raw_messages.reverse()  # Chronological order (oldest first)
    except Exception as e:
        print(f"⚠️ Could not fetch channel history: {e}")
        return [], ""

    history = []
    for msg in raw_messages:
        content = (msg.clean_content or "").strip()
        if not content:
            continue

        # Skip prefix bot commands in history
        if content.startswith("!"):
            continue

        # Determine turn role
        if msg.author == bot.user:
            role = "model"
            text = content
        elif not getattr(msg.author, "bot", False):
            role = "user"
            text = f"{msg.author.display_name}: {content}"
        else:
            # Skip messages from other bots
            continue

        # Merge consecutive messages with identical role
        if history and history[-1]["role"] == role:
            history[-1]["parts"][0] += f"\n{text}"
        else:
            history.append({"role": role, "parts": [text]})

    # Gemini requires history to start with 'user'
    while history and history[0]["role"] != "user":
        history.pop(0)

    # Gemini requires history to end with 'model' so the new user message continues the turn.
    # Preserve any trailing unanswered user messages to be merged into the current prompt.
    trailing_parts = []
    while history and history[-1]["role"] != "model":
        trailing_turn = history.pop(-1)
        if trailing_turn["role"] == "user":
            trailing_parts.extend(trailing_turn["parts"])

    trailing_user_text = "\n".join(reversed(trailing_parts)) if trailing_parts else ""

    return history, trailing_user_text


async def handle_ai_chat(message: discord.Message):
    """Generates an intelligent conversational response using Gemini for messages in #ai-chat."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        await message.reply(
            "⚠️ Gemini API key is not configured. Please set `GEMINI_API_KEY` in your `.env` file."
        )
        return

    model = get_ai_model()
    if model is None:
        await message.reply(
            "⚠️ Could not initialize the Gemini AI model. Please verify your `GEMINI_API_KEY`."
        )
        return

    try:
        async with message.channel.typing():
            history, trailing_user_text = await build_gemini_history(
                message.channel,
                message,
                limit=GEMINI_HISTORY_LIMIT
            )
            chat = model.start_chat(history=history)
            current_text = f"{message.author.display_name}: {message.clean_content}"
            prompt = f"{trailing_user_text}\n{current_text}" if trailing_user_text else current_text
            response = await chat.send_message_async(prompt)

            response_text = getattr(response, "text", "")
            if not response_text:
                response_text = "I'm sorry, I couldn't generate a response to that."

            chunks = split_message(response_text)
            for idx, chunk in enumerate(chunks):
                if idx == 0:
                    await message.reply(chunk, allowed_mentions=discord.AllowedMentions.none())
                else:
                    await message.channel.send(chunk, allowed_mentions=discord.AllowedMentions.none())
    except Exception as e:
        print(f"❌ Gemini AI error: {e}")
        await message.reply(
            "⚠️ Sorry, I encountered an error while communicating with Gemini. Please try again later."
        )


# ── Discord Events ─────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user or getattr(message.author, "bot", None) is True:  # ignore bots
        return

    channel_name = getattr(message.channel, "name", "").lower()
    is_ai_channel = (channel_name == AI_CHANNEL_NAME)

    # If the message is in the designated AI channel (#ai-chat)
    if is_ai_channel:
        # Allow prefix commands like !help or !ping in #ai-chat
        if message.content.startswith("!"):
            await bot.process_commands(message)
            return

        # Respond intelligently using Gemini with context window
        if message.content.strip():
            await handle_ai_chat(message)
        return

    # In other channels: completely ignore AI to prevent spam
    content = message.content.lower().strip()
    if not message.content.startswith("!") and content in ["hi", "hello", "hey"]:
        await message.reply(f"Hey {message.author.mention}! 👋 How's it going?")

    await bot.process_commands(message)


@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel is None:
        channel = member.guild.system_channel

    if channel:
        embed = discord.Embed(
            title="🎉 Welcome to the Server!",
            description=f"Hey {member.mention}, welcome to **{member.guild.name}**! We are glad to have you here.",
            color=discord.Color.green()
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        embed.add_field(name="Member Count", value=f"#{member.guild.member_count}", inline=True)
        embed.set_footer(text=f"User ID: {member.id}")

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            if member.guild.system_channel and channel != member.guild.system_channel:
                await member.guild.system_channel.send(embed=embed)


# ── Slash & Prefix Commands ────────────────────────────────────────────────
@bot.hybrid_command(name="ping", description="Checks the bot's response time and API latency.")
async def ping(ctx: commands.Context):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")


@bot.hybrid_command(name="hello", description="Sends a friendly greeting.")
async def hello(ctx: commands.Context):
    await ctx.send(f"Hello, {ctx.author.mention}! 👋")


@bot.hybrid_command(name="help", description="Displays interactive command list.")
async def help(ctx: commands.Context):
    embed = discord.Embed(
        title="🤖 Astragon Commands",
        description="Here is the list of available commands (usable via `/` or `!`):",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="`/ping` (or `!ping`)",
        value="Checks the bot's response time and API latency.",
        inline=False
    )
    embed.add_field(
        name="`/hello` (or `!hello`)",
        value="Sends a friendly greeting.",
        inline=False
    )
    embed.add_field(
        name="`/help` (or `!help`)",
        value="Displays this interactive help message.",
        inline=False
    )
    embed.add_field(
        name=f"💬 #{AI_CHANNEL_NAME} AI Chat",
        value=f"Chat intelligently with Google Gemini AI in the `#{AI_CHANNEL_NAME}` channel with conversational context.",
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    await ctx.send(embed=embed)


# Owner-only command for instant manual re-syncing if needed
@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context):
    synced = await bot.tree.sync()
    await ctx.send(f"✅ Synced {len(synced)} command(s) to Discord.")


if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
