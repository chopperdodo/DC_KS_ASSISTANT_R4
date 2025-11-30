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

@bot.command()
async def sync(ctx):
    """Syncs slash commands to the current guild for instant updates."""
    try:
        # Sync to the current guild (instant)
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Synced {len(synced)} command(s) to this server!")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync: {e}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await database.init_db()
    print("Database initialized.")
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        
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
