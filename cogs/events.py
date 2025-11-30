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
            # Parse base time as UTC
            start_time = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M")
            # Ensure it's treated as UTC (though naive datetime is fine if we are consistent)
        except ValueError:
            await interaction.followup.send("Invalid time format. Please use `YYYY-MM-DD HH:MM` (e.g., 2025-11-30 13:00)", ephemeral=True)
            return

        interval_delta = self.parse_interval(interval)
        if repeat > 0 and not interval_delta:
            await interaction.followup.send("If you specify repeats, you must provide a valid interval (e.g., `1d`, `12h`).", ephemeral=True)
            return

        events_created = []
        current_time = start_time

        # Add the initial event
        await database.add_event(name, current_time, "") # Description removed as per request
        events_created.append(current_time)

        # Add repeats
        for _ in range(repeat):
            current_time += interval_delta
            await database.add_event(name, current_time, "")
            events_created.append(current_time)

        # Format response
        msg = f"✅ Created **{len(events_created)}** event(s) for **{name}** starting at `{start_time} UTC`."
        if repeat > 0:
            msg += f"\nRepeats: {repeat} times, Interval: {interval}"
            msg += f"\nLast event: `{events_created[-1]} UTC`"
        
        await interaction.followup.send(msg)

    @app_commands.command(name="list", description="List upcoming events")
    async def list_events(self, interaction: discord.Interaction):
        events = await database.get_all_events()
        if not events:
            await interaction.response.send_message("No upcoming events.", ephemeral=True)
            return

        embed = discord.Embed(title="📅 Upcoming Events", color=discord.Color.blue())
        
        # Limit to 25 fields (Discord limit)
        for event in events[:25]:
            # Convert string time to datetime
            try:
                dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Fallback
                dt = datetime.datetime.strptime(event['event_time'], "%Y-%m-%d %H:%M:00")
            
            # Create Discord timestamp (Unix timestamp)
            # Assuming stored time is UTC
            unix_ts = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
            
            embed.add_field(
                name=f"{event['name']} (ID: {event['id']})",
                value=f"🕒 <t:{unix_ts}:F> (<t:{unix_ts}:R>)",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delete", description="Delete an event by ID")
    @app_commands.describe(event_id="The ID of the event to delete")
    async def delete_event(self, interaction: discord.Interaction, event_id: int):
        await database.delete_event(event_id)
        await interaction.response.send_message(f"🗑️ Event with ID **{event_id}** deleted.")

async def setup(bot):
    await bot.add_cog(Events(bot))
