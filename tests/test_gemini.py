import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
import bot
from tests.conftest import run_coro, create_mock_message


class TestGeminiAI(unittest.TestCase):
    def setUp(self):
        bot._cached_model = None

    def tearDown(self):
        bot._cached_model = None

    # ── Test split_message ──────────────────────────────────────────────────
    def test_split_message_empty(self):
        self.assertEqual(bot.split_message(""), [])

    def test_split_message_short(self):
        text = "Hello world! This is a short response."
        self.assertEqual(bot.split_message(text, max_length=2000), [text])

    def test_split_message_splits_at_paragraphs(self):
        p1 = "Paragraph 1 " * 100
        p2 = "Paragraph 2 " * 100
        combined = f"{p1}\n\n{p2}"
        chunks = bot.split_message(combined, max_length=len(p1) + 10)
        self.assertTrue(len(chunks) >= 2)
        for chunk in chunks:
            self.assertTrue(len(chunk) <= len(p1) + 10)

    def test_split_message_splits_at_newlines(self):
        l1 = "Line 1 " * 50
        l2 = "Line 2 " * 50
        combined = f"{l1}\n{l2}"
        chunks = bot.split_message(combined, max_length=len(l1) + 5)
        self.assertTrue(len(chunks) >= 2)

    def test_split_message_splits_at_spaces(self):
        text = "word " * 500
        chunks = bot.split_message(text, max_length=500)
        for chunk in chunks:
            self.assertTrue(len(chunk) <= 500)

    def test_split_message_splits_hard_boundary(self):
        text = "a" * 1500
        chunks = bot.split_message(text, max_length=500)
        self.assertEqual(len(chunks), 3)
        for chunk in chunks:
            self.assertEqual(len(chunk), 500)

    # ── Test build_gemini_history ───────────────────────────────────────────
    def test_build_gemini_history_basic(self):
        """Verifies chronological formatting of user and model turns."""
        channel = MagicMock(spec=discord.TextChannel)
        current_msg = create_mock_message(content="What is AI?", author_name="Alice")

        msg1 = create_mock_message(content="Hello", author_name="Alice")
        msg2 = create_mock_message(content="Hello Alice! How can I help?", author_name="Astragon")
        msg2.author = bot.bot.user

        async def mock_history(limit, before):
            # Discord channel.history returns newest first
            for m in [msg2, msg1]:
                yield m

        channel.history = mock_history

        history = run_coro(bot.build_gemini_history(channel, current_msg, limit=10))
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertIn("Alice: Hello", history[0]["parts"][0])
        self.assertEqual(history[1]["role"], "model")
        self.assertEqual(history[1]["parts"][0], "Hello Alice! How can I help?")

    def test_build_gemini_history_skips_commands_and_bots(self):
        """Verifies prefix commands and messages from other bots are filtered out."""
        channel = MagicMock(spec=discord.TextChannel)
        current_msg = create_mock_message(content="Hello", author_name="Alice")

        msg1 = create_mock_message(content="!help", author_name="Alice")
        msg2 = create_mock_message(content="Random music bot spam", author_name="Rhythm", is_bot=True)
        msg3 = create_mock_message(content="Valid user question", author_name="Bob")
        msg4 = create_mock_message(content="Valid bot answer", author_name="Astragon")
        msg4.author = bot.bot.user

        async def mock_history(limit, before):
            for m in [msg4, msg3, msg2, msg1]:
                yield m

        channel.history = mock_history

        history = run_coro(bot.build_gemini_history(channel, current_msg, limit=10))
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertIn("Bob: Valid user question", history[0]["parts"][0])
        self.assertEqual(history[1]["role"], "model")

    def test_build_gemini_history_merges_consecutive_same_role(self):
        """Verifies consecutive turns by same role are merged to obey Gemini turn alternation."""
        channel = MagicMock(spec=discord.TextChannel)
        current_msg = create_mock_message(content="Third question", author_name="Alice")

        msg1 = create_mock_message(content="First question", author_name="Alice")
        msg2 = create_mock_message(content="Second question", author_name="Bob")
        msg3 = create_mock_message(content="Answer to both", author_name="Astragon")
        msg3.author = bot.bot.user

        async def mock_history(limit, before):
            for m in [msg3, msg2, msg1]:
                yield m

        channel.history = mock_history

        history = run_coro(bot.build_gemini_history(channel, current_msg, limit=10))
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertIn("First question", history[0]["parts"][0])
        self.assertIn("Second question", history[0]["parts"][0])
        self.assertEqual(history[1]["role"], "model")

    def test_build_gemini_history_ensures_user_start_and_model_end(self):
        """Verifies history leading with model or trailing with user is trimmed safely."""
        channel = MagicMock(spec=discord.TextChannel)
        current_msg = create_mock_message(content="Current message", author_name="Charlie")

        orphan_model = create_mock_message(content="Old bot reply without user", author_name="Astragon")
        orphan_model.author = bot.bot.user

        user_turn = create_mock_message(content="User prompt", author_name="Charlie")
        model_turn = create_mock_message(content="Model reply", author_name="Astragon")
        model_turn.author = bot.bot.user

        trailing_user = create_mock_message(content="Unanswered user message", author_name="Charlie")

        async def mock_history(limit, before):
            for m in [trailing_user, model_turn, user_turn, orphan_model]:
                yield m

        channel.history = mock_history

        history = run_coro(bot.build_gemini_history(channel, current_msg, limit=10))
        # After merging and trimming: orphan_model dropped (starts with user),
        # trailing_user dropped (must end with model before current message continues turn)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[-1]["role"], "model")

    def test_build_gemini_history_handles_exception(self):
        """Verifies history building returns empty list if channel history fails."""
        channel = MagicMock(spec=discord.TextChannel)
        current_msg = create_mock_message()
        channel.history.side_effect = Exception("Channel access forbidden")

        history = run_coro(bot.build_gemini_history(channel, current_msg))
        self.assertEqual(history, [])

    # ── Test handle_ai_chat ─────────────────────────────────────────────────
    @patch.dict("os.environ", {}, clear=True)
    def test_handle_ai_chat_missing_api_key(self):
        """Verifies a clear error is sent if GEMINI_API_KEY is not configured."""
        msg = create_mock_message(content="Hello", channel_name="ai-chat")
        run_coro(bot.handle_ai_chat(msg))
        msg.reply.assert_awaited_once()
        args = msg.reply.call_args[0][0]
        self.assertIn("Gemini API key is not configured", args)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"})
    @patch("bot.get_ai_model")
    def test_handle_ai_chat_success(self, mock_get_model):
        """Verifies successful prompt dispatch and reply delivery."""
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hello! I am Gemini AI."
        mock_chat.send_message_async = AsyncMock(return_value=mock_response)
        mock_model.start_chat.return_value = mock_chat
        mock_get_model.return_value = mock_model

        msg = create_mock_message(content="What is Python?", channel_name="ai-chat")

        run_coro(bot.handle_ai_chat(msg))

        mock_model.start_chat.assert_called_once()
        mock_chat.send_message_async.assert_awaited_once()
        msg.reply.assert_awaited_once_with("Hello! I am Gemini AI.")

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"})
    @patch("bot.get_ai_model")
    def test_handle_ai_chat_multichunk_response(self, mock_get_model):
        """Verifies messages longer than 2000 characters are sent in multiple chunks."""
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        # Create 3500-char text
        mock_response.text = ("This is a long AI response paragraph.\n\n" * 90)
        mock_chat.send_message_async = AsyncMock(return_value=mock_response)
        mock_model.start_chat.return_value = mock_chat
        mock_get_model.return_value = mock_model

        msg = create_mock_message(content="Give me a very long explanation", channel_name="ai-chat")

        run_coro(bot.handle_ai_chat(msg))

        msg.reply.assert_awaited_once()
        msg.channel.send.assert_awaited()
        total_chunks = 1 + msg.channel.send.await_count
        self.assertTrue(total_chunks >= 2)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"})
    @patch("bot.get_ai_model")
    def test_handle_ai_chat_exception_handling(self, mock_get_model):
        """Verifies API exceptions are caught and a friendly message is returned."""
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(side_effect=Exception("API Quota Exceeded"))
        mock_model.start_chat.return_value = mock_chat
        mock_get_model.return_value = mock_model

        msg = create_mock_message(content="Trigger error", channel_name="ai-chat")

        run_coro(bot.handle_ai_chat(msg))

        msg.reply.assert_awaited_once()
        args = msg.reply.call_args[0][0]
        self.assertIn("Sorry, I encountered an error while communicating with Gemini", args)

    # ── Test on_message routing and isolation ────────────────────────────────
    @patch("bot.handle_ai_chat", new_callable=AsyncMock)
    def test_on_message_triggers_ai_chat_in_ai_channel(self, mock_handle_ai):
        """Verifies messages in #ai-chat trigger handle_ai_chat."""
        msg = create_mock_message(content="Hello AI!", channel_name="ai-chat")

        with patch.object(bot.bot, "process_commands", new_callable=AsyncMock) as mock_process:
            run_coro(bot.on_message(msg))
            mock_handle_ai.assert_awaited_once_with(msg)
            mock_process.assert_not_awaited()

    @patch("bot.handle_ai_chat", new_callable=AsyncMock)
    def test_on_message_ignores_other_channels_for_ai(self, mock_handle_ai):
        """Verifies messages in #general or other channels NEVER trigger handle_ai_chat."""
        msg = create_mock_message(content="Can you help me?", channel_name="general")

        with patch.object(bot.bot, "process_commands", new_callable=AsyncMock) as mock_process:
            run_coro(bot.on_message(msg))
            mock_handle_ai.assert_not_awaited()
            mock_process.assert_awaited_once_with(msg)

    @patch("bot.handle_ai_chat", new_callable=AsyncMock)
    def test_on_message_ai_channel_allows_prefix_commands(self, mock_handle_ai):
        """Verifies !commands in #ai-chat route to command processor, not handle_ai_chat."""
        msg = create_mock_message(content="!ping", channel_name="ai-chat")

        with patch.object(bot.bot, "process_commands", new_callable=AsyncMock) as mock_process:
            run_coro(bot.on_message(msg))
            mock_handle_ai.assert_not_awaited()
            mock_process.assert_awaited_once_with(msg)

    @patch("bot.handle_ai_chat", new_callable=AsyncMock)
    def test_on_message_ignores_other_bots_in_ai_channel(self, mock_handle_ai):
        """Verifies messages from other bots in #ai-chat are ignored."""
        msg = create_mock_message(content="Bot message", channel_name="ai-chat", is_bot=True)

        with patch.object(bot.bot, "process_commands", new_callable=AsyncMock) as mock_process:
            run_coro(bot.on_message(msg))
            mock_handle_ai.assert_not_awaited()
            mock_process.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
