import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
import bot


def run_coro(coro):
    return asyncio.run(coro)


def create_mock_member(id=12345, name="TestUser", position=5):
    member = MagicMock(spec=discord.Member)
    member.id = id
    member.name = name
    member.display_name = name
    member.mention = f"<@{id}>"
    member.bot = False

    role = MagicMock()
    role.position = position
    member.top_role = role

    member.kick = AsyncMock()
    member.ban = AsyncMock()
    member.send = AsyncMock()
    return member


def create_mock_context(is_slash=False, is_thread=False):
    ctx = MagicMock(spec=commands.Context)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 99999
    ctx.guild.name = "Test Guild"
    ctx.guild.owner_id = 11111

    owner = create_mock_member(id=11111, name="Owner", position=100)
    ctx.guild.owner = owner

    bot_member = create_mock_member(id=99999, name="AstragonBot", position=10)
    ctx.guild.me = bot_member

    author = create_mock_member(id=22222, name="ModUser", position=20)
    ctx.author = author

    if is_thread:
        channel = MagicMock(spec=discord.Thread)
    else:
        channel = MagicMock(spec=discord.TextChannel)

    perms = MagicMock(spec=discord.Permissions)
    perms.send_messages = True
    perms.send_messages_in_threads = True
    perms.kick_members = True
    perms.ban_members = True
    channel.permissions_for.return_value = perms
    ctx.channel = channel

    ctx.send = AsyncMock()
    ctx.defer = AsyncMock()

    if is_slash:
        ctx.interaction = MagicMock()
    else:
        ctx.interaction = None

    return ctx


class TestModerationCommands(unittest.TestCase):
    # ── Kick Command Tests ──────────────────────────────────────────────────
    def test_kick_missing_channel_send_permission_slash(self):
        ctx = create_mock_context(is_slash=True)
        ctx.channel.permissions_for.return_value.send_messages = False
        member = create_mock_member()

        run_coro(bot.kick.callback(ctx, member, reason="Test"))
        ctx.send.assert_awaited_once_with(
            "❌ I cannot perform moderation actions in channels where I cannot send messages.",
            ephemeral=True
        )
        ctx.defer.assert_not_awaited()
        member.kick.assert_not_awaited()

    def test_kick_missing_channel_send_permission_prefix(self):
        ctx = create_mock_context(is_slash=False)
        ctx.channel.permissions_for.return_value.send_messages = False
        member = create_mock_member()

        run_coro(bot.kick.callback(ctx, member, reason="Test"))
        ctx.author.send.assert_awaited_once_with(
            "❌ I cannot perform moderation actions in channels where I cannot send messages."
        )
        ctx.defer.assert_not_awaited()
        member.kick.assert_not_awaited()

    def test_kick_missing_thread_permission_prefix(self):
        ctx = create_mock_context(is_slash=False, is_thread=True)
        ctx.channel.permissions_for.return_value.send_messages = True
        ctx.channel.permissions_for.return_value.send_messages_in_threads = False
        member = create_mock_member()

        run_coro(bot.kick.callback(ctx, member, reason="Test"))
        ctx.author.send.assert_awaited_once_with(
            "❌ I cannot perform moderation actions in channels where I cannot send messages."
        )
        ctx.defer.assert_not_awaited()
        member.kick.assert_not_awaited()

    def test_kick_thread_permission_allowed_when_send_messages_false(self):
        ctx = create_mock_context(is_slash=False, is_thread=True)
        ctx.channel.permissions_for.return_value.send_messages = False
        ctx.channel.permissions_for.return_value.send_messages_in_threads = True
        member = create_mock_member(position=3)

        run_coro(bot.kick.callback(ctx, member, reason="Test"))
        ctx.defer.assert_awaited_once()
        member.kick.assert_awaited_once_with(reason="Test")

    def test_kick_self_rejected(self):
        ctx = create_mock_context()
        member = ctx.author

        run_coro(bot.kick.callback(ctx, member, reason="Self kick"))
        ctx.send.assert_awaited_once_with("❌ You cannot kick yourself.")
        member.kick.assert_not_awaited()

    def test_kick_bot_rejected(self):
        ctx = create_mock_context()
        member = ctx.guild.me

        run_coro(bot.kick.callback(ctx, member, reason="Bot kick"))
        ctx.send.assert_awaited_once_with("❌ I cannot kick myself.")
        member.kick.assert_not_awaited()

    def test_kick_target_higher_than_author_rejected(self):
        ctx = create_mock_context()
        member = create_mock_member(position=25)  # author is 20

        run_coro(bot.kick.callback(ctx, member, reason="Test"))
        ctx.send.assert_awaited_once_with(
            "❌ You cannot kick a member with an equal or higher role than yours."
        )
        member.kick.assert_not_awaited()

    def test_kick_owner_bypasses_author_role_check(self):
        ctx = create_mock_context()
        ctx.author = ctx.guild.owner
        member = create_mock_member(position=100)

        run_coro(bot.kick.callback(ctx, member, reason="Owner kick"))
        member.kick.assert_awaited_once_with(reason="Owner kick")

    def test_kick_target_higher_than_bot_rejected(self):
        ctx = create_mock_context()
        ctx.author.top_role.position = 20
        member = create_mock_member(position=15)  # bot is 10

        run_coro(bot.kick.callback(ctx, member, reason="Test"))
        ctx.send.assert_awaited_once_with(
            "❌ I cannot kick this member because their role is equal to or higher than my highest role."
        )
        member.kick.assert_not_awaited()

    def test_kick_reason_exceeds_512_chars_rejected(self):
        ctx = create_mock_context()
        member = create_mock_member(position=3)
        long_reason = "a" * 513

        run_coro(bot.kick.callback(ctx, member, reason=long_reason))
        ctx.send.assert_awaited_once_with(
            "❌ Reason exceeds Discord's 512-character limit. Please shorten your reason."
        )
        ctx.defer.assert_not_awaited()
        member.kick.assert_not_awaited()

    def test_kick_success(self):
        ctx = create_mock_context()
        member = create_mock_member(position=3)

        run_coro(bot.kick.callback(ctx, member, reason="Spamming"))
        ctx.defer.assert_awaited_once()
        member.kick.assert_awaited_once_with(reason="Spamming")
        ctx.send.assert_awaited_once()

        call_args, call_kwargs = ctx.send.call_args
        embed = call_kwargs.get("embed")
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Member Kicked", embed.title)
        self.assertIn(member.mention, embed.description)

    def test_kick_channel_send_forbidden_falls_back_to_dm(self):
        ctx = create_mock_context()
        member = create_mock_member(position=3)
        ctx.send.side_effect = discord.Forbidden(MagicMock(), "Cannot send message in channel")

        run_coro(bot.kick.callback(ctx, member, reason="Spamming"))
        member.kick.assert_awaited_once_with(reason="Spamming")
        ctx.author.send.assert_awaited_once()
        sent_text = ctx.author.send.call_args[0][0]
        self.assertIn("Successfully kicked", sent_text)
        self.assertIn(str(member.id), sent_text)

    # ── Ban Command Tests ───────────────────────────────────────────────────
    def test_ban_missing_channel_send_permission_slash(self):
        ctx = create_mock_context(is_slash=True)
        ctx.channel.permissions_for.return_value.send_messages = False
        member = create_mock_member()

        run_coro(bot.ban.callback(ctx, member, reason="Test"))
        ctx.send.assert_awaited_once_with(
            "❌ I cannot perform moderation actions in channels where I cannot send messages.",
            ephemeral=True
        )
        ctx.defer.assert_not_awaited()
        member.ban.assert_not_awaited()

    def test_ban_missing_channel_send_permission_prefix(self):
        ctx = create_mock_context(is_slash=False)
        ctx.channel.permissions_for.return_value.send_messages = False
        member = create_mock_member()

        run_coro(bot.ban.callback(ctx, member, reason="Test"))
        ctx.author.send.assert_awaited_once_with(
            "❌ I cannot perform moderation actions in channels where I cannot send messages."
        )
        ctx.defer.assert_not_awaited()
        member.ban.assert_not_awaited()

    def test_ban_missing_thread_permission_prefix(self):
        ctx = create_mock_context(is_slash=False, is_thread=True)
        ctx.channel.permissions_for.return_value.send_messages = True
        ctx.channel.permissions_for.return_value.send_messages_in_threads = False
        member = create_mock_member()

        run_coro(bot.ban.callback(ctx, member, reason="Test"))
        ctx.author.send.assert_awaited_once_with(
            "❌ I cannot perform moderation actions in channels where I cannot send messages."
        )
        ctx.defer.assert_not_awaited()
        member.ban.assert_not_awaited()

    def test_ban_self_rejected(self):
        ctx = create_mock_context()
        member = ctx.author

        run_coro(bot.ban.callback(ctx, member, reason="Self ban"))
        ctx.send.assert_awaited_once_with("❌ You cannot ban yourself.")
        member.ban.assert_not_awaited()

    def test_ban_bot_rejected(self):
        ctx = create_mock_context()
        member = ctx.guild.me

        run_coro(bot.ban.callback(ctx, member, reason="Bot ban"))
        ctx.send.assert_awaited_once_with("❌ I cannot ban myself.")
        member.ban.assert_not_awaited()

    def test_ban_target_higher_than_author_rejected(self):
        ctx = create_mock_context()
        member = create_mock_member(position=25)

        run_coro(bot.ban.callback(ctx, member, reason="Test"))
        ctx.send.assert_awaited_once_with(
            "❌ You cannot ban a member with an equal or higher role than yours."
        )
        member.ban.assert_not_awaited()

    def test_ban_target_higher_than_bot_rejected(self):
        ctx = create_mock_context()
        member = create_mock_member(position=15)

        run_coro(bot.ban.callback(ctx, member, reason="Test"))
        ctx.send.assert_awaited_once_with(
            "❌ I cannot ban this member because their role is equal to or higher than my highest role."
        )
        member.ban.assert_not_awaited()

    def test_ban_reason_exceeds_512_chars_rejected(self):
        ctx = create_mock_context()
        member = create_mock_member(position=3)
        long_reason = "b" * 513

        run_coro(bot.ban.callback(ctx, member, reason=long_reason))
        ctx.send.assert_awaited_once_with(
            "❌ Reason exceeds Discord's 512-character limit. Please shorten your reason."
        )
        ctx.defer.assert_not_awaited()
        member.ban.assert_not_awaited()

    def test_ban_preserves_message_history(self):
        ctx = create_mock_context()
        member = create_mock_member(position=3)

        run_coro(bot.ban.callback(ctx, member, reason="Advertising"))
        ctx.defer.assert_awaited_once()
        member.ban.assert_awaited_once_with(reason="Advertising", delete_message_seconds=0)
        ctx.send.assert_awaited_once()

        call_args, call_kwargs = ctx.send.call_args
        embed = call_kwargs.get("embed")
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Member Banned", embed.title)

    def test_ban_channel_send_forbidden_falls_back_to_dm(self):
        ctx = create_mock_context()
        member = create_mock_member(position=3)
        ctx.send.side_effect = discord.Forbidden(MagicMock(), "Cannot send message in channel")

        run_coro(bot.ban.callback(ctx, member, reason="Advertising"))
        member.ban.assert_awaited_once_with(reason="Advertising", delete_message_seconds=0)
        ctx.author.send.assert_awaited_once()
        sent_text = ctx.author.send.call_args[0][0]
        self.assertIn("Successfully banned", sent_text)
        self.assertIn(str(member.id), sent_text)

    # ── Error Handler Tests ─────────────────────────────────────────────────
    def test_kick_error_missing_permissions(self):
        ctx = create_mock_context()
        error = commands.MissingPermissions(["kick_members"])
        run_coro(bot.kick_error(ctx, error))
        ctx.send.assert_awaited_once_with("🚫 You do not have permission to kick members.")

    def test_kick_error_bot_missing_permissions(self):
        ctx = create_mock_context()
        error = commands.BotMissingPermissions(["kick_members"])
        run_coro(bot.kick_error(ctx, error))
        ctx.send.assert_awaited_once_with("❌ I do not have permission to kick members.")

    def test_ban_error_missing_permissions(self):
        ctx = create_mock_context()
        error = commands.MissingPermissions(["ban_members"])
        run_coro(bot.ban_error(ctx, error))
        ctx.send.assert_awaited_once_with("🚫 You do not have permission to ban members.")

    def test_ban_error_bot_missing_permissions(self):
        ctx = create_mock_context()
        error = commands.BotMissingPermissions(["ban_members"])
        run_coro(bot.ban_error(ctx, error))
        ctx.send.assert_awaited_once_with("❌ I do not have permission to ban members.")


if __name__ == "__main__":
    unittest.main()
