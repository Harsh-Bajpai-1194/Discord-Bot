import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import discord
from discord.ext import commands
import bot


def run_coro(coro):
    """Executes a coroutine synchronously by stepping it until completion."""
    while True:
        try:
            coro.send(None)
        except StopIteration as e:
            return e.value


def create_mock_context():
    ctx = MagicMock(spec=commands.Context)
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.display_name = "TestAuthor"
    ctx.author.mention = "<@12345>"
    return ctx


class MockAsyncContextManager:
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def create_mock_session(mock_resp):
    mock_session = MagicMock()
    mock_session.get.return_value = MockAsyncContextManager(mock_resp)
    return MockAsyncContextManager(mock_session)


class TestApiCommands(unittest.TestCase):
    # ── Joke Command Tests ──────────────────────────────────────────────────
    def test_joke_success_twopart(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={
            "type": "twopart",
            "setup": "Why do programmers wear glasses?",
            "delivery": "Because they need C#!",
            "category": "Programming"
        })

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.joke.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once()
        call_kwargs = ctx.send.call_args[1]
        embed = call_kwargs["embed"]
        self.assertIn("Why do programmers wear glasses?", embed.description)
        self.assertIn("Because they need C#!", embed.description)

    def test_joke_success_single(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={
            "type": "single",
            "joke": "A SQL statement walks into a bar and asks two tables, 'Can I join you?'",
            "category": "Programming"
        })

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.joke.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once()
        call_kwargs = ctx.send.call_args[1]
        embed = call_kwargs["embed"]
        self.assertIn("SQL statement", embed.description)

    def test_joke_api_error_status(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 500

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.joke.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Failed to fetch a joke from the API. Please try again later.")

    def test_joke_non_mapping_response(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=["not", "a", "dict"])

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.joke.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Failed to fetch a joke from the API. Please try again later.")

    def test_joke_api_error_payload(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"error": True, "message": "No jokes found"})

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.joke.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Failed to fetch a joke from the API. Please try again later.")

    def test_joke_network_exception(self):
        ctx = create_mock_context()
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection refused")

        with patch("aiohttp.ClientSession", return_value=MockAsyncContextManager(mock_session)):
            run_coro(bot.joke.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Network error while fetching a joke.")

    # ── Fact Command Tests ──────────────────────────────────────────────────
    def test_fact_success(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"text": "Honey never spoils."})

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.fact.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once()
        call_kwargs = ctx.send.call_args[1]
        embed = call_kwargs["embed"]
        self.assertEqual(embed.description, "Honey never spoils.")

    def test_fact_api_error_status(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 502

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.fact.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Failed to fetch a fact from the API. Please try again later.")

    def test_fact_non_mapping_response(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.fact.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Failed to fetch a fact from the API. Please try again later.")

    def test_fact_network_exception(self):
        ctx = create_mock_context()
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Timeout")

        with patch("aiohttp.ClientSession", return_value=MockAsyncContextManager(mock_session)):
            run_coro(bot.fact.callback(ctx))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Network error while fetching a fact.")

    # ── Weather Command Tests (OpenWeatherMap) ──────────────────────────────
    @patch.dict("os.environ", {"OPENWEATHER_API_KEY": "fake_key_123"})
    def test_weather_openweathermap_success(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={
            "name": "London",
            "sys": {"country": "GB"},
            "main": {"temp": 15.2, "humidity": 70},
            "weather": [{"description": "light rain"}],
            "wind": {"speed": 4.5}
        })
        mock_session = MagicMock()
        mock_session.get.return_value = MockAsyncContextManager(mock_resp)

        with patch("aiohttp.ClientSession", return_value=MockAsyncContextManager(mock_session)):
            run_coro(bot.weather.callback(ctx, city="London#"))

        ctx.defer.assert_awaited_once()
        mock_session.get.assert_called_once()
        args, kwargs = mock_session.get.call_args
        self.assertEqual(args[0], "https://api.openweathermap.org/data/2.5/weather")
        self.assertEqual(kwargs["params"], {"q": "London#", "appid": "fake_key_123", "units": "metric"})

        ctx.send.assert_awaited_once()
        embed = ctx.send.call_args[1]["embed"]
        self.assertIn("London, GB", embed.title)
        self.assertEqual(embed.fields[0].value, "Light Rain")
        self.assertEqual(embed.fields[1].value, "15°C")

    @patch.dict("os.environ", {"OPENWEATHER_API_KEY": "fake_key_123"})
    def test_weather_openweathermap_city_not_found(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 404

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.weather.callback(ctx, city="NoSuchCity123"))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ City **NoSuchCity123** not found.")

    @patch.dict("os.environ", {"OPENWEATHER_API_KEY": "fake_key_123"})
    def test_weather_openweathermap_non_mapping_response(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value="unexpected string")

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.weather.callback(ctx, city="Paris"))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Error fetching weather from OpenWeatherMap.")

    # ── Weather Command Tests (wttr.in Fallback) ────────────────────────────
    @patch.dict("os.environ", {}, clear=True)
    def test_weather_wttr_fallback_success(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={
            "current_condition": [{
                "temp_C": "20",
                "weatherDesc": [{"value": "Sunny"}],
                "humidity": "50",
                "windspeedKmph": "15"
            }],
            "nearest_area": [{
                "areaName": [{"value": "Tokyo"}],
                "country": [{"value": "Japan"}]
            }]
        })
        mock_session = MagicMock()
        mock_session.get.return_value = MockAsyncContextManager(mock_resp)

        with patch("aiohttp.ClientSession", return_value=MockAsyncContextManager(mock_session)):
            run_coro(bot.weather.callback(ctx, city="Tokyo#"))

        ctx.defer.assert_awaited_once()
        mock_session.get.assert_called_once()
        args, kwargs = mock_session.get.call_args
        self.assertEqual(args[0], "https://wttr.in/Tokyo%23")
        self.assertEqual(kwargs["params"], {"format": "j1"})

        ctx.send.assert_awaited_once()
        embed = ctx.send.call_args[1]["embed"]
        self.assertIn("Tokyo, Japan", embed.title)
        self.assertEqual(embed.fields[0].value, "Sunny")
        self.assertEqual(embed.fields[1].value, "20°C")

    @patch.dict("os.environ", {}, clear=True)
    def test_weather_wttr_non_mapping_response(self):
        ctx = create_mock_context()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=[])

        with patch("aiohttp.ClientSession", return_value=create_mock_session(mock_resp)):
            run_coro(bot.weather.callback(ctx, city="Berlin"))

        ctx.defer.assert_awaited_once()
        ctx.send.assert_awaited_once_with("❌ Could not retrieve weather for **Berlin**.")

    # ── Error Handler Test ──────────────────────────────────────────────────
    def test_weather_error_missing_arg(self):
        ctx = create_mock_context()
        error = commands.MissingRequiredArgument(MagicMock())
        run_coro(bot.weather_error(ctx, error))
        ctx.send.assert_awaited_once_with("⚠️ Usage: `!weather <city>` or `/weather <city>`")


if __name__ == "__main__":
    unittest.main()
