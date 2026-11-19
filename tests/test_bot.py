import unittest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
import discord
from discord.ext import commands
import bot
from tests.conftest import run_coro


class TestAstragonBotGeneral(unittest.TestCase):
    def test_flask_keep_alive(self):
        """Verify the Flask keep-alive server returns 200 OK for Render."""
        client = bot.app.test_client()
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode('utf-8'), "Bot is alive!")

    def test_bot_intents_and_commands(self):
        """Verify required Discord intents and registered commands."""
        self.assertTrue(bot.bot.intents.message_content)
        self.assertTrue(bot.bot.intents.members)

        command_names = {cmd.name for cmd in bot.bot.commands}
        expected_commands = {'ping', 'hello', 'help', 'sync'}
        self.assertTrue(expected_commands.issubset(command_names))

    def test_ping_command(self):
        """Verify ping command returns formatted latency."""
        ctx = MagicMock()
        ctx.send = AsyncMock()

        with patch.object(type(bot.bot), 'latency', new_callable=PropertyMock) as mock_lat:
            mock_lat.return_value = 0.045
            run_coro(bot.ping.callback(ctx))

        ctx.send.assert_awaited_once_with("🏓 Pong! Latency: 45ms")

    def test_hello_command(self):
        """Verify hello command greets the message author."""
        ctx = MagicMock()
        ctx.author.mention = "<@123456789>"
        ctx.send = AsyncMock()

        run_coro(bot.hello.callback(ctx))
        ctx.send.assert_awaited_once_with("Hello, <@123456789>! 👋")

    def test_help_command(self):
        """Verify help command builds and dispatches the command embed."""
        ctx = MagicMock()
        ctx.author.display_name = "TestUser"
        ctx.send = AsyncMock()

        run_coro(bot.help.callback(ctx))
        ctx.send.assert_awaited_once()

        call_args, call_kwargs = ctx.send.call_args
        embed = call_kwargs.get("embed")
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Astragon Commands", embed.title)
        field_names = [field.name for field in embed.fields]
        self.assertTrue(any("ping" in name for name in field_names))
        self.assertTrue(any("hello" in name for name in field_names))
        self.assertTrue(any("help" in name for name in field_names))
        self.assertTrue(any("AI Chat" in name for name in field_names))

    def test_on_message_ignores_bot(self):
        """Verify on_message ignores messages sent by the bot itself."""
        message = MagicMock()
        message.author = bot.bot.user

        with patch.object(bot.bot, "process_commands", new_callable=AsyncMock) as mock_process:
            run_coro(bot.on_message(message))
            mock_process.assert_not_awaited()

    def test_on_message_greets_friendly_text_in_general_channel(self):
        """Verify on_message replies to greetings in non-AI channels and processes commands."""
        message = MagicMock()
        message.author = MagicMock()
        message.author.bot = False
        message.author.mention = "<@999>"
        message.channel.name = "general"
        message.content = "Hello"
        message.reply = AsyncMock()

        with patch.object(bot.bot, "process_commands", new_callable=AsyncMock) as mock_process:
            run_coro(bot.on_message(message))
            message.reply.assert_awaited_once_with("Hey <@999>! 👋 How's it going?")
            mock_process.assert_awaited_once_with(message)

    def test_on_message_prefix_command_skips_greeting(self):
        """Verify messages starting with ! are not greeted as plain text."""
        message = MagicMock()
        message.author = MagicMock()
        message.author.bot = False
        message.channel.name = "general"
        message.content = "!hello"
        message.reply = AsyncMock()

        with patch.object(bot.bot, "process_commands", new_callable=AsyncMock) as mock_process:
            run_coro(bot.on_message(message))
            message.reply.assert_not_awaited()
            mock_process.assert_awaited_once_with(message)

    def test_on_member_join_welcome_channel(self):
        """Verify on_member_join sends a welcome embed to #welcome if present."""
        member = MagicMock(spec=discord.Member)
        member.id = 112233
        member.mention = "<@112233>"
        member.guild.name = "Astragon Guild"
        member.guild.member_count = 42
        member.avatar = MagicMock()
        member.avatar.url = "https://example.com/avatar.png"

        welcome_channel = MagicMock(spec=discord.TextChannel)
        welcome_channel.name = "welcome"
        welcome_channel.send = AsyncMock()
        member.guild.text_channels = [welcome_channel]
        member.guild.system_channel = MagicMock(spec=discord.TextChannel)

        run_coro(bot.on_member_join(member))
        welcome_channel.send.assert_awaited_once()
        call_args, call_kwargs = welcome_channel.send.call_args
        embed = call_kwargs.get("embed")
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Welcome to the Server!", embed.title)
        self.assertIn("Astragon Guild", embed.description)

    def test_sync_command_success(self):
        """Verify sync command triggers bot tree sync and reports count."""
        ctx = MagicMock()
        ctx.send = AsyncMock()

        with patch.object(bot.bot.tree, "sync", new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = ["ping", "hello", "help"]
            run_coro(bot.sync.callback(ctx))
            mock_sync.assert_awaited_once()
            ctx.send.assert_awaited_once_with("✅ Synced 3 command(s) to Discord.")


if __name__ == "__main__":
    unittest.main()
