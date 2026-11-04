import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()  # loads .env file

# ── Keep-alive server (required for Render Web Service) ──────────────────────
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_server, daemon=True).start()
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

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:  # ignore the bot's own messages
        return

    content = message.content.lower().strip()

    # Only reply to plain messages, NOT to bot commands like !hello
    if not message.content.startswith("!") and content in ["hi", "hello", "hey"]:
        await message.reply(f"Hey {message.author.mention}! 👋 How's it going?")

    await bot.process_commands(message)  # still allow !commands to work

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

    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    await ctx.send(embed=embed)

# Owner-only command for instant manual re-syncing if needed
@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context):
    synced = await bot.tree.sync()
    await ctx.send(f"✅ Synced {len(synced)} command(s) to Discord.")

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
