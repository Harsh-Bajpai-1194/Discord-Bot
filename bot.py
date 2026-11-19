import discord
from discord.ext import commands
import os
import re
from datetime import timedelta
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

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user or getattr(message.author, "bot", None) is True:  # ignore bots
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
                try:
                    await member.guild.system_channel.send(embed=embed)
                except discord.Forbidden:
                    pass

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
        name="`/kick` (or `!kick`)",
        value="Kicks a member from the server (Requires Kick Members permission).",
        inline=False
    )
    embed.add_field(
        name="`/ban` (or `!ban`)",
        value="Bans a member from the server (Requires Ban Members permission).",
        inline=False
    )
    embed.add_field(
        name="`/timeout` (or `!timeout`)",
        value="Times out a member for a specified duration (Requires Moderate Members permission).",
        inline=False
    )
    embed.add_field(
        name="`/untimeout` (or `!untimeout`)",
        value="Removes timeout from a member (Requires Moderate Members permission).",
        inline=False
    )
    embed.add_field(
        name="`/purge` (or `!purge`, `!clear`)",
        value="Bulk deletes recent messages (1-100) (Requires Manage Messages permission).",
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    await ctx.send(embed=embed)

# ── Duration Parsing Helper ────────────────────────────────────────────────
TIME_UNITS = {
    's': 1,
    'm': 60,
    'h': 3600,
    'd': 86400,
}

DURATION_PATTERN = re.compile(r'^(\d+\s*[smhd]\s*)+$', re.IGNORECASE)
PART_PATTERN = re.compile(r'(\d+)\s*([smhd])', re.IGNORECASE)

def parse_duration(duration_str: str) -> timedelta:
    """
    Parses a duration string (e.g., '10s', '10m', '1h', '1d', '1h30m') into a timedelta.
    Supports up to Discord's 28-day max limit.
    """
    if not duration_str or not isinstance(duration_str, str):
        raise ValueError("Duration cannot be empty.")

    cleaned = duration_str.strip()
    if not DURATION_PATTERN.match(cleaned):
        raise ValueError(f"Invalid duration format: '{duration_str}'. Use formats like 10s, 10m, 1h, 1d.")

    matches = PART_PATTERN.findall(cleaned)
    if not matches:
        raise ValueError(f"Invalid duration format: '{duration_str}'. Use formats like 10s, 10m, 1h, 1d.")

    total_seconds = sum(int(amount) * TIME_UNITS[unit.lower()] for amount, unit in matches)

    if total_seconds <= 0:
        raise ValueError("Timeout duration must be greater than 0 seconds.")

    max_seconds = 28 * 86400  # 28 days
    if total_seconds > max_seconds:
        raise ValueError("Timeout duration cannot exceed 28 days.")

    return timedelta(seconds=total_seconds)


# ── Moderation Channel Permission Helper ──────────────────────────────────
def check_channel_send_permissions(ctx: commands.Context) -> bool:
    """Checks if the bot has permission to send messages in the current channel or thread."""
    if not ctx.guild or not ctx.channel:
        return False
    perms = ctx.channel.permissions_for(ctx.guild.me)
    if isinstance(ctx.channel, discord.Thread):
        return getattr(perms, 'send_messages_in_threads', False)
    return getattr(perms, 'send_messages', False)


# ── Moderation Commands ───────────────────────────────────────────────────

@bot.hybrid_command(name="purge", aliases=["clear"], description="Bulk delete recent messages (1-100).")
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True, read_message_history=True, embed_links=True)
async def purge(ctx: commands.Context, amount: int):
    """Delete a number of recent messages from the channel.
    Limits:
    - amount must be between 1 and 100
    - Discord does not allow bulk deletion of messages older than 14 days
    """
    if amount < 1 or amount > 100:
        await ctx.send("❌ Amount must be between 1 and 100.", ephemeral=True)
        return

    if not check_channel_send_permissions(ctx):
        if ctx.interaction is not None:
            await ctx.send("❌ I cannot perform moderation actions in channels where I cannot send messages.", ephemeral=True)
        else:
            try:
                await ctx.author.send("❌ I cannot perform moderation actions in channels where I cannot send messages.")
            except discord.Forbidden:
                pass
        return

    await ctx.defer()
    try:
        deleted = await ctx.channel.purge(limit=amount, bulk=True)
        embed = discord.Embed(
            title="🧹 Messages Purged",
            description=f"Selected {len(deleted)} message(s) for deletion.",
            color=discord.Color.dark_gray()
        )
        msg = await ctx.send(embed=embed)
        await msg.delete(delay=5)
    except discord.Forbidden:
        await ctx.send("❌ I lack permissions to delete messages in this channel.", ephemeral=True)
    except discord.HTTPException as e:
        # Discord returns code 50034 for messages older than 14 days
        if getattr(e, "code", None) == 50034:
            await ctx.send("⚠️ Cannot purge messages older than 14 days. The purge may be incomplete; please check remaining message history before retrying.", ephemeral=True)
        else:
            await ctx.send(f"❌ An error occurred: {e}. The purge may be incomplete; please check remaining message history before retrying.", ephemeral=True)

@bot.hybrid_command(name="iclear", description="Alias for /purge command.")
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True, read_message_history=True, embed_links=True)
async def iclear(ctx: commands.Context, amount: int):
    await purge.callback(ctx, amount)

@purge.error
async def purge_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You do not have permission to manage messages.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I lack required permissions to purge messages.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Invalid argument. Usage: `/purge <amount>` where amount is 1-100.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ This command can only be used in a server.")
    else:
        await ctx.send(f"⚠️ An error occurred: {error}")

@iclear.error
async def iclear_error(ctx: commands.Context, error: commands.CommandError):
    await purge_error(ctx, error)


@bot.hybrid_command(name="kick", description="Kicks a member from the server.")
@commands.guild_only()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if not check_channel_send_permissions(ctx):
        if ctx.interaction is not None:
            await ctx.send("❌ I cannot perform moderation actions in channels where I cannot send messages.", ephemeral=True)
        else:
            try:
                await ctx.author.send("❌ I cannot perform moderation actions in channels where I cannot send messages.")
            except discord.Forbidden:
                pass
        return

    if member == ctx.author:
        await ctx.send("❌ You cannot kick yourself.")
        return

    if member == ctx.guild.me:
        await ctx.send("❌ I cannot kick myself.")
        return

    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner and getattr(ctx.guild, 'owner_id', None) != ctx.author.id:
        await ctx.send("❌ You cannot kick a member with an equal or higher role than yours.")
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ I cannot kick this member because their role is equal to or higher than my highest role.")
        return

    await ctx.defer()
    await member.kick(reason=reason)

    embed = discord.Embed(
        title="👢 Member Kicked",
        description=f"**{member.mention}** has been kicked from the server.",
        color=discord.Color.orange()
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text=f"User ID: {member.id}")

    await ctx.send(embed=embed)

@kick.error
async def kick_error(ctx: commands.Context, error: commands.CommandError):
    try:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You do not have permission to kick members.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I do not have permission to kick members.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ Member not found. Please mention a valid server member.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Usage: `!kick @user [reason]` or `/kick <user> [reason]`")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ This command can only be used in a server.")
        else:
            await ctx.send(f"⚠️ An error occurred: {error}")
    except discord.Forbidden:
        try:
            await ctx.author.send("❌ I could not respond in that channel due to missing Send Messages permission.")
        except discord.Forbidden:
            pass


@bot.hybrid_command(name="ban", description="Bans a member from the server.")
@commands.guild_only()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if not check_channel_send_permissions(ctx):
        if ctx.interaction is not None:
            await ctx.send("❌ I cannot perform moderation actions in channels where I cannot send messages.", ephemeral=True)
        else:
            try:
                await ctx.author.send("❌ I cannot perform moderation actions in channels where I cannot send messages.")
            except discord.Forbidden:
                pass
        return

    if member == ctx.author:
        await ctx.send("❌ You cannot ban yourself.")
        return

    if member == ctx.guild.me:
        await ctx.send("❌ I cannot ban myself.")
        return

    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner and getattr(ctx.guild, 'owner_id', None) != ctx.author.id:
        await ctx.send("❌ You cannot ban a member with an equal or higher role than yours.")
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ I cannot ban this member because their role is equal to or higher than my highest role.")
        return

    await ctx.defer()
    try:
        await member.ban(reason=reason, delete_message_seconds=0)
    except TypeError:
        await member.ban(reason=reason, delete_message_days=0)

    embed = discord.Embed(
        title="🔨 Member Banned",
        description=f"**{member.mention}** has been banned from the server.",
        color=discord.Color.red()
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text=f"User ID: {member.id}")

    await ctx.send(embed=embed)

@ban.error
async def ban_error(ctx: commands.Context, error: commands.CommandError):
    try:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You do not have permission to ban members.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I do not have permission to ban members.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ Member not found. Please mention a valid server member.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Usage: `!ban @user [reason]` or `/ban <user> [reason]`")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ This command can only be used in a server.")
        else:
            await ctx.send(f"⚠️ An error occurred: {error}")
    except discord.Forbidden:
        try:
            await ctx.author.send("❌ I could not respond in that channel due to missing Send Messages permission.")
        except discord.Forbidden:
            pass


@bot.hybrid_command(name="timeout", description="Times out a member in the server.")
@commands.guild_only()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def timeout(ctx: commands.Context, member: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
    if not check_channel_send_permissions(ctx):
        if ctx.interaction is not None:
            await ctx.send("❌ I cannot perform moderation actions in channels where I cannot send messages.", ephemeral=True)
        else:
            try:
                await ctx.author.send("❌ I cannot perform moderation actions in channels where I cannot send messages.")
            except discord.Forbidden:
                pass
        return

    if member == ctx.author:
        await ctx.send("❌ You cannot timeout yourself.")
        return

    if member == ctx.guild.me:
        await ctx.send("❌ I cannot timeout myself.")
        return

    if member == ctx.guild.owner or (getattr(ctx.guild, 'owner_id', None) is not None and member.id == ctx.guild.owner_id):
        await ctx.send("❌ You cannot timeout the server owner.")
        return

    author_is_owner = (ctx.author == ctx.guild.owner or (getattr(ctx.guild, 'owner_id', None) is not None and ctx.author.id == ctx.guild.owner_id))
    if member.top_role >= ctx.author.top_role and not author_is_owner:
        await ctx.send("❌ You cannot timeout a member with an equal or higher role than yours.")
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ I cannot timeout this member because their role is equal to or higher than my highest role.")
        return

    try:
        delta = parse_duration(duration)
    except (ValueError, commands.BadArgument) as e:
        await ctx.send(f"⚠️ {e}", allowed_mentions=discord.AllowedMentions.none())
        return

    await ctx.defer()
    until = discord.utils.utcnow() + delta
    await member.timeout(until, reason=reason)

    embed = discord.Embed(
        title="⏳ Member Timed Out",
        description=f"**{member.mention}** has been timed out.",
        color=discord.Color.gold()
    )
    embed.add_field(name="Target", value=member.mention, inline=True)
    embed.add_field(name="Duration", value=duration, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"User ID: {member.id}")

    await ctx.send(embed=embed)


@timeout.error
async def timeout_error(ctx: commands.Context, error: commands.CommandError):
    try:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You do not have permission to timeout members.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I do not have permission to timeout members.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ Member not found. Please mention a valid server member.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Usage: `!timeout @user [duration] [reason]` or `/timeout <user> [duration] [reason]`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"⚠️ {error}", allowed_mentions=discord.AllowedMentions.none())
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ This command can only be used in a server.")
        else:
            await ctx.send(f"⚠️ An error occurred: {error}")
    except discord.Forbidden:
        try:
            await ctx.author.send("❌ I could not respond in that channel due to missing Send Messages permission.")
        except discord.Forbidden:
            pass


@bot.hybrid_command(name="untimeout", description="Removes timeout from a member in the server.")
@commands.guild_only()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def untimeout(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if not check_channel_send_permissions(ctx):
        if ctx.interaction is not None:
            await ctx.send("❌ I cannot perform moderation actions in channels where I cannot send messages.", ephemeral=True)
        else:
            try:
                await ctx.author.send("❌ I cannot perform moderation actions in channels where I cannot send messages.")
            except discord.Forbidden:
                pass
        return

    if member == ctx.author:
        await ctx.send("❌ You cannot untimeout yourself.")
        return

    if member == ctx.guild.me:
        await ctx.send("❌ I cannot untimeout myself.")
        return

    if member == ctx.guild.owner or (getattr(ctx.guild, 'owner_id', None) is not None and member.id == ctx.guild.owner_id):
        await ctx.send("❌ You cannot untimeout the server owner.")
        return

    author_is_owner = (ctx.author == ctx.guild.owner or (getattr(ctx.guild, 'owner_id', None) is not None and ctx.author.id == ctx.guild.owner_id))
    if member.top_role >= ctx.author.top_role and not author_is_owner:
        await ctx.send("❌ You cannot untimeout a member with an equal or higher role than yours.")
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ I cannot untimeout this member because their role is equal to or higher than my highest role.")
        return

    await ctx.defer()
    await member.timeout(None, reason=reason)

    embed = discord.Embed(
        title="🔊 Member Timeout Removed",
        description=f"**{member.mention}**'s timeout has been removed.",
        color=discord.Color.green()
    )
    embed.add_field(name="Target", value=member.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"User ID: {member.id}")

    await ctx.send(embed=embed)


@untimeout.error
async def untimeout_error(ctx: commands.Context, error: commands.CommandError):
    try:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 You do not have permission to remove timeouts.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I do not have permission to timeout members.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ Member not found. Please mention a valid server member.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Usage: `!untimeout @user [reason]` or `/untimeout <user> [reason]`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"⚠️ {error}")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ This command can only be used in a server.")
        else:
            await ctx.send(f"⚠️ An error occurred: {error}")
    except discord.Forbidden:
        try:
            await ctx.author.send("❌ I could not respond in that channel due to missing Send Messages permission.")
        except discord.Forbidden:
            pass


# Owner-only command for instant manual re-syncing if needed
@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context):
    synced = await bot.tree.sync()
    await ctx.send(f"✅ Synced {len(synced)} command(s) to Discord.")

@sync.error
async def sync_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.NotOwner):
        await ctx.send("🚫 Only the bot owner can use this command.")
    else:
        await ctx.send(f"⚠️ Sync failed: {error}")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
