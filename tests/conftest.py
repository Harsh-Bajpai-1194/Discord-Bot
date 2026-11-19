import sys
from pathlib import Path

# Add project root to sys.path so 'import bot' resolves reliably
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands


def run_coro(coro):
    """
    Executes a coroutine synchronously by stepping through mock awaits.
    Works universally without requiring OS network/loopback sockets.
    """
    while True:
        try:
            coro.send(None)
        except StopIteration as e:
            return e.value


def create_mock_context(is_slash=False, is_thread=False):
    """Helper to construct a realistic Discord Context mock."""
    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 99999
    ctx.guild.name = "Test Guild"
    ctx.guild.owner_id = 11111

    owner = MagicMock(spec=discord.Member)
    owner.id = 11111
    owner.mention = "<@11111>"
    ctx.guild.owner = owner

    bot_member = MagicMock(spec=discord.Member)
    bot_member.id = 99999
    bot_member.mention = "<@99999>"
    ctx.guild.me = bot_member

    author = MagicMock(spec=discord.Member)
    author.id = 22222
    author.mention = "<@22222>"
    author.display_name = "TestUser"
    author.send = AsyncMock()
    ctx.author = author

    if is_thread:
        channel = MagicMock(spec=discord.Thread)
    else:
        channel = MagicMock(spec=discord.TextChannel)
    channel.mention = "<#33333>"
    channel.name = "general"

    perms = MagicMock()
    perms.send_messages = True
    perms.send_messages_in_threads = True
    channel.permissions_for.return_value = perms
    ctx.channel = channel

    ctx.interaction = MagicMock() if is_slash else None
    ctx.send = AsyncMock()
    ctx.defer = AsyncMock()

    return ctx


def create_mock_message(content="Hello", author_name="TestUser", is_bot=False, channel_name="general", is_bot_user=False):
    """Helper to construct a realistic Discord Message mock."""
    msg = MagicMock(spec=discord.Message)
    msg.content = content
    msg.clean_content = content

    author = MagicMock(spec=discord.Member)
    author.display_name = author_name
    author.mention = f"<@{hash(author_name) % 100000}>"
    author.bot = is_bot
    msg.author = author

    channel = MagicMock(spec=discord.TextChannel)
    channel.name = channel_name
    channel.send = AsyncMock()
    channel.history = MagicMock()
    msg.channel = channel

    msg.reply = AsyncMock()
    return msg
