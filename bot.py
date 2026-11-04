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
intents.members = True # For member join/leave events

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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

        await channel.send(embed=embed)
        
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.mention}! 👋")

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 Astragon Commands",
        description="Here is the list of available commands:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="`!ping`",
        value="Checks the bot's response time and API latency.",
        inline=False
    )
    embed.add_field(
        name="`!hello`",
        value="Sends a friendly greeting",
        inline=False
    )
    embed.add_field(
        name="`!help`",
        value="Displays this interacive help message.",
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author.display_name}")

    await ctx.send(embed=embed)

bot.run(os.getenv("DISCORD_TOKEN"))
