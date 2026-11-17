import discord
from discord.ext import commands
import os
import aiohttp
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

# ── General Commands ───────────────────────────────────────────────────────
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
        name="`/joke` (or `!joke`)",
        value="Tells a random family-friendly joke.",
        inline=False
    )
    embed.add_field(
        name="`/fact` (or `!fact`)",
        value="Shares a random interesting fact.",
        inline=False
    )
    embed.add_field(
        name="`/weather <city>` (or `!weather`)",
        value="Displays current weather for a specified city.",
        inline=False
    )
    embed.add_field(
        name="`/help` (or `!help`)",
        value="Displays this interactive help message.",
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    await ctx.send(embed=embed)

# ── Fun & Utility API Commands ─────────────────────────────────────────────
@bot.hybrid_command(name="joke", description="Tells a random safe joke.")
async def joke(ctx: commands.Context):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://v2.jokeapi.dev/joke/Any?safe-mode", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    await ctx.send("❌ Failed to fetch a joke from the API. Please try again later.")
                    return
                data = await resp.json()
        except Exception:
            await ctx.send("❌ Network error while fetching a joke.")
            return

    embed = discord.Embed(title="😂 Random Joke", color=discord.Color.gold())
    if data.get("type") == "twopart":
        embed.description = f"**{data.get('setup')}**\n\n*{data.get('delivery')}*"
    else:
        embed.description = data.get("joke", "No joke found.")
    embed.set_footer(text=f"Category: {data.get('category', 'General')} | Requested by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="fact", description="Shares a random interesting fact.")
async def fact(ctx: commands.Context):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    await ctx.send("❌ Failed to fetch a fact from the API. Please try again later.")
                    return
                data = await resp.json()
        except Exception:
            await ctx.send("❌ Network error while fetching a fact.")
            return

    fact_text = data.get("text", "No fact available.")
    embed = discord.Embed(
        title="💡 Did You Know?",
        description=fact_text,
        color=discord.Color.teal()
    )
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="weather", description="Fetches current weather for a specified city.")
async def weather(ctx: commands.Context, *, city: str):
    api_key = os.getenv("OPENWEATHER_API_KEY")
    async with aiohttp.ClientSession() as session:
        try:
            if api_key:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 404:
                        await ctx.send(f"❌ City **{city}** not found.")
                        return
                    if resp.status != 200:
                        await ctx.send("❌ Error fetching weather from OpenWeatherMap.")
                        return
                    data = await resp.json()
                    temp_c = round(data["main"]["temp"])
                    desc = data["weather"][0]["description"].title()
                    humidity = data["main"]["humidity"]
                    wind = f"{data['wind']['speed']} m/s"
                    city_name = f"{data['name']}, {data['sys'].get('country', '')}"
            else:
                headers = {"User-Agent": "curl/7.68.0"}
                url = f"https://wttr.in/{city}?format=j1"
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status != 200:
                        await ctx.send(f"❌ Could not retrieve weather for **{city}**.")
                        return
                    data = await resp.json()
                    current = data["current_condition"][0]
                    temp_c = current["temp_C"]
                    desc = current["weatherDesc"][0]["value"]
                    humidity = current["humidity"]
                    wind = f"{current['windspeedKmph']} km/h"
                    area = data.get("nearest_area", [{}])[0]
                    area_name = area.get("areaName", [{}])[0].get("value", city.title())
                    country = area.get("country", [{}])[0].get("value", "")
                    city_name = f"{area_name}, {country}" if country else area_name
        except Exception:
            await ctx.send("❌ Network error while fetching weather data.")
            return

    embed = discord.Embed(
        title=f"🌤️ Weather for {city_name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Condition", value=desc, inline=True)
    embed.add_field(name="Temperature", value=f"{temp_c}°C", inline=True)
    embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
    embed.add_field(name="Wind Speed", value=wind, inline=True)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@weather.error
async def weather_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Usage: `!weather <city>` or `/weather <city>`")
    else:
        await ctx.send(f"⚠️ Error: {error}")

# Owner-only command for instant manual re-syncing if needed
@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context):
    synced = await bot.tree.sync()
    await ctx.send(f"✅ Synced {len(synced)} command(s) to Discord.")

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
