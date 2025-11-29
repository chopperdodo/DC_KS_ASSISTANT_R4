import discord
from discord.ext import commands
import datetime
import database

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.announcement_channel_id = None

    @commands.group(invoke_without_command=True)
    async def event(self, ctx):
        await ctx.send("Available commands: `!event add`, `!event list`, `!event delete`")

    @event.command(name="add")
    @commands.has_permissions(administrator=True) # Or check for specific role
    async def add_event(self, ctx, name: str, time_str: str, *, description: str):
        """
        Add an event. Format: !event add "Name" "YYYY-MM-DD HH:MM" "Description"
        """
        try:
            event_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await ctx.send("Invalid time format. Please use YYYY-MM-DD HH:MM")
            return

        await database.add_event(name, event_time, description)
        await ctx.send(f"Event '{name}' added for {event_time}!")

    @event.command(name="list")
    async def list_events(self, ctx):
        events = await database.get_all_events()
        if not events:
            await ctx.send("No upcoming events.")
            return

        embed = discord.Embed(title="Upcoming Events", color=discord.Color.blue())
        for event in events:
            # event is a Row object, can access by name
            embed.add_field(
                name=f"{event['name']} (ID: {event['id']})",
                value=f"Time: {event['event_time']}\n{event['description']}",
                inline=False
            )
        await ctx.send(embed=embed)

    @event.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def delete_event(self, ctx, event_id: int):
        await database.delete_event(event_id)
        await ctx.send(f"Event with ID {event_id} deleted.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel: discord.TextChannel):
        """Sets the announcement channel."""
        self.bot.announcement_channel_id = channel.id
        # In a real app, save this to DB or config file so it persists restart
        # For now, we'll just keep it in memory or rely on .env default
        await ctx.send(f"Announcement channel set to {channel.mention}")

async def setup(bot):
    await bot.add_cog(Events(bot))
