import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
import database

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global variable to store channel ID (can be updated at runtime)
bot.announcement_channel_id = os.getenv("ANNOUNCEMENT_CHANNEL_ID")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await database.init_db()
    print("Database initialized.")
    print("------")

async def main():
    async with bot:
        # Load extensions
        await bot.load_extension("cogs.events")
        await bot.load_extension("cogs.scheduler")
        
        token = os.getenv("DISCORD_TOKEN")
        if not token or token == "your_token_here":
            print("Error: DISCORD_TOKEN not found in .env or is default value.")
            return
        
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        pass
