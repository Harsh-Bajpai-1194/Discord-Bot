import discord
from discord.ext import commands
import os
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

    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    await ctx.send(embed=embed)

# ── Moderation Commands ───────────────────────────────────────────────────

@bot.hybrid_command(name="kick", description="Kicks a member from the server.")
@commands.guild_only()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True, send_messages=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
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

    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
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
            await ctx.send("❌ I do not have permission to kick members and send messages in this channel.")
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
@commands.bot_has_permissions(ban_members=True, send_messages=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
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

    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        await ctx.send("❌ You cannot ban a member with an equal or higher role than yours.")
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ I cannot ban this member because their role is equal to or higher than my highest role.")
        return

    await ctx.defer()
    await member.ban(reason=reason)

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
            await ctx.send("❌ I do not have permission to ban members and send messages in this channel.")
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


# Owner-only command for instant manual re-syncing if needed
@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context):
    synced = await bot.tree.sync()
    await ctx.send(f"✅ Synced {len(synced)} command(s) to Discord.")

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
